import os
import sys
import re
import platform
import threading
import time
from datetime import datetime
from tkinter import filedialog, messagebox
import shutil

import customtkinter as ctk

import config
import ftp_client
import utils

class CommonMixin:
    """Popups e utilitários de UI compartilhados entre NBS e Apollo."""

    def open_extension_cleanup_popup(self, system_name):
        """Abre uma janela pop-up modal para pesquisar e excluir arquivos por extensão específica (ex: .log, .tmp)."""
        c = self.app_config

        # Create window
        popup = ctk.CTkToplevel(self)
        title_suffix = "NBS" if system_name == "nbs" else "Linx"
        popup.title(f"Limpeza por Extensão - {title_suffix}")
        screen_h = self.winfo_screenheight()
        target_h = min(660, max(460, screen_h - 100))
        popup.geometry(f"640x{target_h}")
        popup.minsize(520, 420)
        popup.grab_set()  # Make modal

        # Title labels
        ctk.CTkLabel(popup, text=f"Utilitário de Limpeza por Extensão - {title_suffix}", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Top Control Frame (Directory selection + Path details)
        top_ctrl = ctk.CTkFrame(popup)
        top_ctrl.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        top_ctrl.grid_columnconfigure(0, weight=1)
        top_ctrl.grid_columnconfigure(1, weight=3)
        top_ctrl.grid_columnconfigure(2, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        folder_label_text = "Pasta NBS a Limpar:" if system_name == "nbs" else "Pasta Linx a Limpar:"
        ctk.CTkLabel(top_ctrl, text=folder_label_text, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        custom_path_var = ctk.StringVar(value="")

        # Directory resolution helper
        def get_resolved_path(dir_key):
            if system_name == "nbs":
                if dir_key == "C:\\NBS":
                    return c.get("nbs_path_win", "C:\\NBS") if self.os_type == "Windows" else c.get("nbs_path_linux", "./NBS_Local")
            else: # linx
                if dir_key == "C:\\Apollo":
                    return "C:\\Apollo" if self.os_type == "Windows" else "./Apollo"
                elif dir_key == "C:\\3camadas":
                    return "C:\\3camadas" if self.os_type == "Windows" else "./3Camadas"
            
            if dir_key == "Outro Diretório...":
                return custom_path_var.get()
            return ""

        # OptionMenu selection
        default_val = "C:\\NBS" if system_name == "nbs" else "C:\\Apollo"
        menu_values = ["C:\\NBS", "Outro Diretório..."] if system_name == "nbs" else ["C:\\Apollo", "C:\\3camadas", "Outro Diretório..."]
        
        dir_var = ctk.StringVar(value=default_val)
        dir_label_path = ctk.CTkLabel(popup, text="Caminho: -", font=ctk.CTkFont(size=11, slant="italic"), anchor="w")
        dir_label_path.grid(row=2, column=0, padx=20, pady=(2, 8), sticky="w")

        # Extension Input Frame (Row 3)
        ext_input_frame = ctk.CTkFrame(popup)
        ext_input_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        ext_input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ext_input_frame, text="Extensão de arquivo (ex: .log, .tmp, .zip):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        ext_entry = ctk.CTkEntry(ext_input_frame, placeholder_text=".log")
        ext_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        ext_entry.insert(0, ".log")

        # Search/Filter Frame (Row 4)
        filter_frame = ctk.CTkFrame(popup)
        filter_frame.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(filter_frame, text="Pesquisa / Filtro (Glob/Regex):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        
        filter_entry_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_entry_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        filter_entry_frame.grid_columnconfigure(0, weight=1)

        filter_entry = ctk.CTkEntry(filter_entry_frame, placeholder_text="Ex: *log* ou ^NBSErr.*\\.log$")
        filter_entry.grid(row=0, column=0, sticky="ew")

        # Selection tracking dictionaries
        all_files_found = []
        file_checkboxes_widgets = []
        checkbox_selections = {} # Stores {filepath: BooleanVar}

        # Scroll frame for items list (Row 5)
        scroll_frame = ctk.CTkScrollableFrame(popup, label_text="Arquivos Encontrados")
        scroll_frame.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")
        popup.grid_rowconfigure(5, weight=1)

        # Glob / Regex matching logic
        import fnmatch
        import re

        def matches_pattern(filename, pattern):
            if not pattern:
                return True
            pattern = pattern.strip()
            if "*" in pattern or "?" in pattern:
                try:
                    return fnmatch.fnmatchcase(filename.lower(), pattern.lower())
                except Exception:
                    pass
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                return bool(regex.search(filename))
            except Exception:
                pass
            return pattern.lower() in filename.lower()

        # Render list based on filter
        def populate_list():
            for w in file_checkboxes_widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
            file_checkboxes_widgets.clear()

            target_path = get_resolved_path(dir_var.get())
            dir_label_path.configure(text=f"Diretório ativo: {os.path.abspath(target_path)}")

            if not os.path.exists(target_path):
                err_lbl = ctk.CTkLabel(scroll_frame, text="Caminho do diretório não encontrado no sistema.", font=ctk.CTkFont(slant="italic"))
                err_lbl.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                file_checkboxes_widgets.append(err_lbl)
                return

            filter_text = filter_entry.get().strip()

            filtered_files = []
            for f in all_files_found:
                if matches_pattern(f, filter_text):
                    filtered_files.append(f)

            if not filtered_files:
                ext_str = ext_entry.get().strip()
                empty_lbl = ctk.CTkLabel(scroll_frame, text=f"Nenhum arquivo {ext_str} corresponde à pesquisa.", font=ctk.CTkFont(slant="italic"))
                empty_lbl.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                file_checkboxes_widgets.append(empty_lbl)
                return

            for idx, filename in enumerate(filtered_files):
                full_path = os.path.join(target_path, filename)
                
                if full_path not in checkbox_selections:
                    checkbox_selections[full_path] = ctk.BooleanVar(value=False)
                
                try:
                    stats = os.stat(full_path)
                    size_mb = stats.st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
                    details = f" ({size_mb:.2f} MB) - {mtime}"
                except Exception:
                    details = ""

                chk = ctk.CTkCheckBox(scroll_frame, text=f"{filename}{details}", variable=checkbox_selections[full_path])
                chk.grid(row=idx, column=0, padx=10, pady=4, sticky="w")
                file_checkboxes_widgets.append(chk)

        # Scans directory and resets files tracking
        def browse_custom_dir():
            from tkinter import filedialog
            selected = filedialog.askdirectory(parent=popup, title="Selecionar pasta para limpeza")
            if selected:
                custom_path_var.set(selected)
                dir_var.set("Outro Diretório...")
                scan_directory()

        def scan_directory():
            all_files_found.clear()
            checkbox_selections.clear()
            
            target_path = get_resolved_path(dir_var.get())
            if dir_var.get() == "Outro Diretório..." and not target_path:
                browse_custom_dir()
                return

            ext_str = ext_entry.get().strip().lower()
            if not ext_str.startswith("."):
                ext_str = "." + ext_str

            if os.path.exists(target_path):
                try:
                    for name in os.listdir(target_path):
                        if os.path.isfile(os.path.join(target_path, name)):
                            name_lower = name.lower()
                            if name_lower.endswith(ext_str):
                                all_files_found.append(name)
                    all_files_found.sort()
                except Exception as err:
                    print(f"Erro ao escanear diretório: {str(err)}")
            populate_list()

        # Selection helpers for filtered items
        def select_filtered(state):
            filter_text = filter_entry.get().strip()
            target_path = get_resolved_path(dir_var.get())
            
            for filename in all_files_found:
                if matches_pattern(filename, filter_text):
                    full_path = os.path.join(target_path, filename)
                    if full_path in checkbox_selections:
                        checkbox_selections[full_path].set(state)

        # Bind events
        ext_entry.bind("<Return>", lambda e: scan_directory())
        ext_entry.bind("<FocusOut>", lambda e: scan_directory())

        # UI Actions
        dir_menu = ctk.CTkOptionMenu(top_ctrl, variable=dir_var, values=menu_values, command=lambda v: scan_directory())
        dir_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        btn_browse = ctk.CTkButton(top_ctrl, text="Pesquisar...", width=95, command=browse_custom_dir)
        btn_browse.grid(row=0, column=2, padx=(0, 10), pady=5)

        # Search/Filter action buttons
        btn_apply = ctk.CTkButton(filter_entry_frame, text="Filtrar", width=80, command=populate_list)
        btn_apply.grid(row=0, column=1, padx=(5, 0))

        btn_clear = ctk.CTkButton(filter_entry_frame, text="Limpar", width=80, fg_color="transparent", border_width=1, command=lambda: [filter_entry.delete(0, "end"), populate_list()])
        btn_clear.grid(row=0, column=2, padx=(5, 0))

        # Search button next to extension entry
        btn_search_ext = ctk.CTkButton(ext_input_frame, text="Buscar arquivos", width=120, command=scan_directory)
        btn_search_ext.grid(row=0, column=2, padx=10, pady=8)

        # Selection Control Row (Row 6)
        sel_ctrl_frame = ctk.CTkFrame(popup, fg_color="transparent")
        sel_ctrl_frame.grid(row=6, column=0, padx=20, pady=2, sticky="ew")
        sel_ctrl_frame.grid_columnconfigure(0, weight=1)
        sel_ctrl_frame.grid_columnconfigure(1, weight=1)

        btn_check_all = ctk.CTkButton(sel_ctrl_frame, text="Marcar Filtrados", height=24, fg_color="#34495e", hover_color="#2c3e50", font=ctk.CTkFont(size=11), command=lambda: select_filtered(True))
        btn_check_all.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        btn_uncheck_all = ctk.CTkButton(sel_ctrl_frame, text="Desmarcar Filtrados", height=24, fg_color="#34495e", hover_color="#2c3e50", font=ctk.CTkFont(size=11), command=lambda: select_filtered(False))
        btn_uncheck_all.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Footer Frame (Row 7)
        footer = ctk.CTkFrame(popup, fg_color="transparent")
        footer.grid(row=7, column=0, padx=20, pady=(10, 15), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        # Delete Action
        def on_delete_clicked():
            to_delete = [path for path, var in checkbox_selections.items() if var.get()]
            if not to_delete:
                messagebox.showwarning("Aviso", "Nenhum arquivo selecionado para exclusão.", parent=popup)
                return
            
            total_sel = len(to_delete)
            confirm_msg = f"Tem certeza de que deseja EXCLUIR DEFINITIVAMENTE os {total_sel} arquivo(s) selecionado(s)?\n\n"
            max_preview = 6
            for p in to_delete[:max_preview]:
                confirm_msg += f"• {os.path.basename(p)}\n"
            
            if total_sel > max_preview:
                confirm_msg += f"\n... e mais {total_sel - max_preview} arquivo(s) selecionado(s)."
            
            confirm = messagebox.askyesno("Confirmar Exclusão", confirm_msg, parent=popup)
            if confirm:
                deleted_count = 0
                errors = []
                for p in to_delete:
                    try:
                        os.remove(p)
                        deleted_count += 1
                    except Exception as err:
                        errors.append(f"{os.path.basename(p)}: {str(err)}")
                
                if errors:
                    max_err_preview = 5
                    err_msg = f"Foram excluídos {deleted_count} de {total_sel} arquivos.\n\nErros ocorridos:\n"
                    err_msg += "\n".join(errors[:max_err_preview])
                    if len(errors) > max_err_preview:
                        err_msg += f"\n... e mais {len(errors) - max_err_preview} erro(s)."
                    messagebox.showerror("Exclusão Parcial", err_msg, parent=popup)
                else:
                    messagebox.showinfo("Sucesso", f"Todos os {deleted_count} arquivos selecionados foram excluídos com sucesso!", parent=popup)
                
                scan_directory()

        delete_btn = ctk.CTkButton(footer, text="Excluir Selecionados", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", height=38, command=on_delete_clicked)
        delete_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        close_btn = ctk.CTkButton(footer, text="Fechar", height=38, fg_color="transparent", border_width=1, command=popup.destroy)
        close_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Load files initial list
        scan_directory()


    def open_powershell_restart_popup(self, system_name="nbs"):
        """Abre uma janela pop-up modal para configurar e enviar o comando de reinício remoto via PowerShell."""
        c = self.app_config

        popup = ctk.CTkToplevel(self)
        sys_title = "NBS" if system_name.lower() == "nbs" else "Linx"
        popup.title(f"Reinício de Servidores via PowerShell - {sys_title}")
        popup.geometry("640x560")
        popup.minsize(540, 500)
        popup.grab_set()

        # Title
        ctk.CTkLabel(popup, text=f"Reinício Remoto de Servidor ({sys_title})", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 2), sticky="w")
        ctk.CTkLabel(popup, text="Disparar o comando PowerShell Restart-Computer -Force para um servidor remoto.", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        popup.grid_columnconfigure(0, weight=1)

        # Form Frame
        form_frame = ctk.CTkFrame(popup)
        form_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # 1. Server Selection / Custom IP
        ctk.CTkLabel(form_frame, text="Servidor Destino (IP/Host):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        servers_list = c.get("servers", [])
        server_options = [s.strip() for s in servers_list if s and s.strip()]
        if "Outro Servidor / IP..." not in server_options:
            server_options.append("Outro Servidor / IP...")

        server_var = ctk.StringVar(value=server_options[0])
        
        server_dropdown = ctk.CTkOptionMenu(form_frame, variable=server_var, values=server_options)
        server_dropdown.grid(row=0, column=1, padx=15, pady=(12, 5), sticky="ew")

        ctk.CTkLabel(form_frame, text="IP ou Nome Personalizado:", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=5, sticky="w")
        custom_server_entry = ctk.CTkEntry(form_frame, placeholder_text="Ex: 192.168.1.100 ou SERVIDOR-02")
        custom_server_entry.grid(row=1, column=1, padx=15, pady=5, sticky="ew")

        def update_entry_state(*args):
            val = server_var.get()
            if val == "Outro Servidor / IP...":
                custom_server_entry.delete(0, "end")
            else:
                custom_server_entry.delete(0, "end")
                custom_server_entry.insert(0, val)

        server_var.trace_add("write", update_entry_state)
        update_entry_state()

        # 2. Force Option Checkbox
        force_var = ctk.BooleanVar(value=True)
        force_chk = ctk.CTkCheckBox(
            form_frame, 
            text="Forçar reinício (-Force) mesmo com usuários conectados", 
            variable=force_var,
            font=ctk.CTkFont(weight="bold")
        )
        force_chk.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="w")

        # 3. Optional Credentials
        ctk.CTkLabel(form_frame, text="Usuário (Opcional):", font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=15, pady=5, sticky="w")
        user_entry = ctk.CTkEntry(form_frame, placeholder_text="Ex: DOMINIO\\Administrador")
        user_entry.grid(row=3, column=1, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Senha (Opcional):", font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=15, pady=(5, 12), sticky="w")
        pass_entry = ctk.CTkEntry(form_frame, placeholder_text="Senha do Usuário", show="*")
        pass_entry.grid(row=4, column=1, padx=15, pady=(5, 12), sticky="ew")

        # Log Textbox inside popup
        log_box = ctk.CTkTextbox(popup, height=130)
        log_box.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        popup.grid_rowconfigure(3, weight=1)

        def append_log(msg):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_box.insert("end", f"[{timestamp}] {msg}\n")
            log_box.see("end")

        # Execute Action
        def execute_reboot():
            target_host = custom_server_entry.get().strip()
            if not target_host or target_host == "Outro Servidor / IP...":
                messagebox.showwarning("Aviso", "Por favor, informe o IP ou nome do servidor de destino.", parent=popup)
                return

            force = force_var.get()
            user = user_entry.get().strip() or None
            password = pass_entry.get().strip() or None

            confirm_msg = (
                f"Tem certeza que deseja reiniciar o servidor '{target_host}'?\n\n"
                f"Atenção: Se a opção -Force estiver marcada, TODOS os usuários conectados no servidor "
                f"serão desconectados imediatamente e tarefas não salvas poderão ser perdidas."
            )
            
            if not messagebox.askyesno("Confirmar Reinício Remoto", confirm_msg, parent=popup, icon="warning"):
                return

            append_log(f"Iniciando solicitação de reinício para '{target_host}'...")
            btn_run.configure(state="disabled", text="Enviando comando...")

            def run_thread():
                try:
                    success = utils.restart_remote_server_powershell(
                        server_name_or_ip=target_host,
                        force=force,
                        user=user,
                        password=password,
                        log_callback=append_log
                    )
                    if success:
                        messagebox.showinfo("Sucesso", f"Comando de reinício enviado com sucesso para {target_host}.", parent=popup)
                    else:
                        messagebox.showerror("Erro", f"Não foi possível reiniciar {target_host}. Verifique os logs para mais detalhes.", parent=popup)
                except Exception as ex:
                    append_log(f"Erro inesperado: {str(ex)}")
                    messagebox.showerror("Erro", f"Exceção durante a execução: {str(ex)}", parent=popup)
                finally:
                    btn_run.configure(state="normal", text="Enviar Comando de Reinício (PowerShell)")

            threading.Thread(target=run_thread, daemon=True).start()

        # Button Frame
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        btn_run = ctk.CTkButton(
            btn_frame, 
            text="Enviar Comando de Reinício (PowerShell)", 
            fg_color="#D32F2F", 
            hover_color="#9A0007",
            font=ctk.CTkFont(weight="bold"),
            height=38,
            command=execute_reboot
        )
        btn_run.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        btn_close = ctk.CTkButton(
            btn_frame, 
            text="Fechar", 
            width=100,
            height=38,
            fg_color="transparent",
            border_width=1,
            command=popup.destroy
        )
        btn_close.grid(row=0, column=1, padx=(5, 0), sticky="e")


