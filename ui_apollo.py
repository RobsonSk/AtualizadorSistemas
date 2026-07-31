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
from changelog import CHANGELOG_APOLLO

class ApolloMixin:
    """Interface, abas e lógica de negócios específica do sistema Apollo/Linx."""

    def setup_tab_linx_about(self):
        tab = self.frame_linx_about
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(tab, text="Sobre o Atualizador Linx", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        # Dev info
        info_frame = ctk.CTkFrame(tab)
        info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_frame, text="Informações do Desenvolvedor e Versão", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        details_text = (
            "Desenvolvedor: Robson Santos\n"
            "Contato: robsonshk@gmail.com\n"
            "Versão do Programa: 1.0.9\n"
            "Finalidade: Facilitar o download, descompactação, aplicação de atualizações e limpeza de arquivos do sistema Linx DMS."
        )
        ctk.CTkLabel(info_frame, text=details_text, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        # Changelog Section
        ctk.CTkLabel(tab, text="Histórico de Alterações do Linx (Changelog)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")

        self.linx_changelog_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="monospace", size=11))
        self.linx_changelog_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.linx_changelog_box.insert("0.0", CHANGELOG_APOLLO)
        self.linx_changelog_box.configure(state="disabled")


    def setup_tab_linx_download(self):
        tab = self.frame_linx_download
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        # Left Column Frame (Parameters)
        self.linx_dl_left_frame = ctk.CTkScrollableFrame(tab)
        self.linx_dl_left_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.linx_dl_left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.linx_dl_left_frame, text="Parâmetros de Execução Linx", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Package selection
        ctk.CTkLabel(self.linx_dl_left_frame, text="Pacote Linx:", anchor="w").grid(row=1, column=0, padx=15, pady=(10, 0), sticky="w")
        self.linx_package_menu = ctk.CTkOptionMenu(self.linx_dl_left_frame, values=["LINXDMS", "HPE", "BRAVOS", "TOYOTA"], command=lambda x: self.save_ui_to_config())
        self.linx_package_menu.grid(row=2, column=0, padx=15, pady=2, sticky="ew")

        # Version entry (saved when starting download or saving manually)
        ctk.CTkLabel(self.linx_dl_left_frame, text="Versão (ex: 5.19):", anchor="w").grid(row=3, column=0, padx=15, pady=(10, 0), sticky="w")
        self.linx_version_entry = ctk.CTkEntry(self.linx_dl_left_frame, placeholder_text="5.19")
        self.linx_version_entry.grid(row=4, column=0, padx=15, pady=2, sticky="ew")
        self.linx_version_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_version_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        # Download path entry (saved when starting download or saving manually)
        ctk.CTkLabel(self.linx_dl_left_frame, text="Diretório de Gravação:", anchor="w").grid(row=5, column=0, padx=15, pady=(10, 0), sticky="w")
        path_frame = ctk.CTkFrame(self.linx_dl_left_frame, fg_color="transparent")
        path_frame.grid(row=6, column=0, padx=15, pady=2, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)
        self.linx_path_entry = ctk.CTkEntry(path_frame)
        self.linx_path_entry.grid(row=0, column=0, sticky="ew")
        self.linx_path_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_path_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_frame, text="...", width=30, command=lambda: self.browse_directory(self.linx_path_entry)).grid(row=0, column=1, padx=(5, 0))

        # Right Column Frame (Options)
        self.linx_dl_right_frame = ctk.CTkScrollableFrame(tab)
        self.linx_dl_right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.linx_dl_right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.linx_dl_right_frame, text="Opções de Download Linx", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Checkboxes for different types of packages
        self.linx_dl_delphi_var = ctk.BooleanVar()
        self.linx_dl_delphi_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Delphi (Download Padrão)", variable=self.linx_dl_delphi_var, command=self.save_ui_to_config)
        self.linx_dl_delphi_check.grid(row=1, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_server_var = ctk.BooleanVar()
        self.linx_dl_server_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="3 Camadas - Server", variable=self.linx_dl_server_var, command=self.save_ui_to_config)
        self.linx_dl_server_check.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_client_var = ctk.BooleanVar()
        self.linx_dl_client_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="3 Camadas - Client", variable=self.linx_dl_client_var, command=self.save_ui_to_config)
        self.linx_dl_client_check.grid(row=3, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_web_var = ctk.BooleanVar()
        self.linx_dl_web_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Instalador Web (LinxDMS Web)", variable=self.linx_dl_web_var, command=self.save_ui_to_config)
        self.linx_dl_web_check.grid(row=4, column=0, padx=15, pady=5, sticky="w")

        # Checkboxes for new modules
        ctk.CTkLabel(self.linx_dl_right_frame, text="Módulos Adicionais & Apoio", font=ctk.CTkFont(size=14, weight="bold")).grid(row=5, column=0, padx=15, pady=(12, 5), sticky="w")

        self.linx_dl_comissoes_var = ctk.BooleanVar()
        self.linx_dl_comissoes_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="DMS Comissões", variable=self.linx_dl_comissoes_var, command=self.save_ui_to_config)
        self.linx_dl_comissoes_check.grid(row=6, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_apoio_trocafornec_var = ctk.BooleanVar()
        self.linx_dl_apoio_trocafornec_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Apoio - Troca Fornecedor", variable=self.linx_dl_apoio_trocafornec_var, command=self.save_ui_to_config)
        self.linx_dl_apoio_trocafornec_check.grid(row=7, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_apoio_trocaserie_var = ctk.BooleanVar()
        self.linx_dl_apoio_trocaserie_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Apoio - Troca Série Transm.", variable=self.linx_dl_apoio_trocaserie_var, command=self.save_ui_to_config)
        self.linx_dl_apoio_trocaserie_check.grid(row=8, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_apoio_verificadiaria_var = ctk.BooleanVar()
        self.linx_dl_apoio_verificadiaria_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Apoio - Verifica Comp. Diária", variable=self.linx_dl_apoio_verificadiaria_var, command=self.save_ui_to_config)
        self.linx_dl_apoio_verificadiaria_check.grid(row=9, column=0, padx=15, pady=5, sticky="w")

        self.linx_dl_integrador_var = ctk.BooleanVar()
        self.linx_dl_integrador_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Linx DMS Integrador", variable=self.linx_dl_integrador_var, command=self.save_ui_to_config)
        self.linx_dl_integrador_check.grid(row=10, column=0, padx=15, pady=5, sticky="w")

        # Opções de Backup
        ctk.CTkLabel(self.linx_dl_right_frame, text="Opções de Backup", font=ctk.CTkFont(size=14, weight="bold")).grid(row=11, column=0, padx=15, pady=(12, 5), sticky="w")

        self.linx_backup_apollo_var = ctk.BooleanVar()
        self.linx_backup_apollo_check = ctk.CTkCheckBox(self.linx_dl_right_frame, text="Backup EXE e DLLs (C:\\Apollo\\atualiza) antes de descompactar", variable=self.linx_backup_apollo_var, command=self.save_ui_to_config)
        self.linx_backup_apollo_check.grid(row=12, column=0, padx=15, pady=5, sticky="w")

        # Bottom Frame (Status, Progress and Launch Button)
        self.linx_dl_bottom_frame = ctk.CTkFrame(tab)
        self.linx_dl_bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        self.linx_dl_bottom_frame.grid_columnconfigure(0, weight=4)
        self.linx_dl_bottom_frame.grid_columnconfigure(1, weight=1)

        # Log & Console
        self.linx_console_log = ctk.CTkTextbox(self.linx_dl_bottom_frame, height=140, font=ctk.CTkFont(family="monospace", size=11))
        self.linx_console_log.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.linx_dl_status_label = ctk.CTkLabel(self.linx_dl_bottom_frame, text="Pronto para iniciar download Linx.", anchor="w")
        self.linx_dl_status_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")

        self.linx_dl_progressbar = ctk.CTkProgressBar(self.linx_dl_bottom_frame)
        self.linx_dl_progressbar.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.linx_dl_progressbar.set(0)

        self.linx_start_dl_btn = ctk.CTkButton(self.linx_dl_bottom_frame, text="Iniciar Processo", font=ctk.CTkFont(size=14, weight="bold"), height=35, command=self.start_linx_download_process)
        self.linx_start_dl_btn.grid(row=1, column=1, rowspan=2, padx=10, pady=5, sticky="nsew")

        self.linx_pause_dl_btn = ctk.CTkButton(self.linx_dl_bottom_frame, text="Pausar", font=ctk.CTkFont(size=13, weight="bold"), height=16, command=self.toggle_linx_pause_download)
        self.linx_cancel_dl_btn = ctk.CTkButton(self.linx_dl_bottom_frame, text="Cancelar", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", height=16, command=self.cancel_linx_download)


    def setup_tab_linx_update(self):
        tab = self.frame_linx_update
        tab.grid_columnconfigure(0, weight=3) # Left (Services)
        tab.grid_columnconfigure(1, weight=4) # Right (Extraction/Update)
        tab.grid_rowconfigure(0, weight=1)

        # Left Frame: Windows Services Control Panel
        self.services_frame = ctk.CTkScrollableFrame(tab)
        self.services_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.services_frame.grid_columnconfigure(0, weight=1)
        self.services_frame.grid_rowconfigure(4, weight=1) # Spacer

        ctk.CTkLabel(self.services_frame, text="Serviços do Windows", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")
        ctk.CTkLabel(self.services_frame, text="Monitoramento e controle em tempo real", font=ctk.CTkFont(size=11, slant="italic")).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # Container for services list
        self.services_list_container = ctk.CTkFrame(self.services_frame, fg_color="transparent")
        self.services_list_container.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.services_list_container.grid_columnconfigure(0, weight=2) # Service Name
        self.services_list_container.grid_columnconfigure(1, weight=1) # Status badge
        self.services_list_container.grid_columnconfigure(2, weight=1) # Action button

        self.service_status_labels = {}
        self.service_action_buttons = {}

        # 3 Services list
        self.build_services_ui()

        # Refresh Services Button
        self.refresh_services_btn = ctk.CTkButton(self.services_frame, text="Atualizar Status", font=ctk.CTkFont(weight="bold"), command=self.refresh_linx_services)
        self.refresh_services_btn.grid(row=3, column=0, padx=15, pady=(15, 5), sticky="ew")

        # Stop Apollo Server Button (*serverapp*)
        self.stop_apolloserver_btn = ctk.CTkButton(self.services_frame, text="Fechar ApolloServer (*serverapp*)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", command=self.stop_apollo_server_process)
        self.stop_apolloserver_btn.grid(row=4, column=0, padx=15, pady=(5, 5), sticky="ew")

        # Custom Process Termination Section (Regex/Name, e.g. wsContabil)
        kill_section_frame = ctk.CTkFrame(self.services_frame, fg_color="transparent")
        kill_section_frame.grid(row=5, column=0, padx=15, pady=(5, 15), sticky="ew")
        kill_section_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(kill_section_frame, text="Fechar Processos (Regex / Nome):", font=ctk.CTkFont(size=11, weight="bold"), anchor="w").grid(row=0, column=0, columnspan=2, pady=(0, 2), sticky="w")

        self.linx_kill_pattern_entry = ctk.CTkEntry(kill_section_frame, placeholder_text="ex: wsContabil ou *serverapp*")
        self.linx_kill_pattern_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        self.linx_kill_pattern_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_kill_pattern_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        self.stop_custom_process_btn = ctk.CTkButton(kill_section_frame, text="Fechar", width=65, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", command=self.stop_process_by_regex)
        self.stop_custom_process_btn.grid(row=1, column=1)


        # Right Frame: Extraction & Installation Panel
        self.update_action_frame = ctk.CTkFrame(tab)
        self.update_action_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.update_action_frame.grid_columnconfigure(0, weight=1)
        self.update_action_frame.grid_rowconfigure(3, weight=1) # Console log takes remaining space

        ctk.CTkLabel(self.update_action_frame, text="Descompactação & Atualização", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")
        
        # Info about destinations
        dest_info = ctk.CTkFrame(self.update_action_frame)
        dest_info.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        dest_info.grid_columnconfigure(0, weight=1)
        
        self.dest_normal_lbl = ctk.CTkLabel(dest_info, text="Apollo/Atualiza: -", anchor="w", justify="left", font=ctk.CTkFont(size=11))
        self.dest_normal_lbl.grid(row=0, column=0, padx=10, pady=2, sticky="w")
        self.dest_server_lbl = ctk.CTkLabel(dest_info, text="3Camadas Server: -", anchor="w", justify="left", font=ctk.CTkFont(size=11))
        self.dest_server_lbl.grid(row=1, column=0, padx=10, pady=2, sticky="w")
        self.dest_client_lbl = ctk.CTkLabel(dest_info, text="3Camadas Client: -", anchor="w", justify="left", font=ctk.CTkFont(size=11))
        self.dest_client_lbl.grid(row=2, column=0, padx=10, pady=2, sticky="w")

        # Command Section
        run_frame = ctk.CTkFrame(self.update_action_frame, fg_color="transparent")
        run_frame.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        run_frame.grid_columnconfigure(0, weight=3)
        run_frame.grid_columnconfigure(1, weight=1)

        self.linx_start_update_btn = ctk.CTkButton(run_frame, text="Iniciar Atualização", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#27ae60", hover_color="#2ecc71", height=38, command=self.start_linx_update_process)
        self.linx_start_update_btn.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Text Console Log
        self.linx_update_console_log = ctk.CTkTextbox(self.update_action_frame, height=200, font=ctk.CTkFont(family="monospace", size=11))
        self.linx_update_console_log.grid(row=3, column=0, padx=15, pady=5, sticky="nsew")
        self.linx_update_console_log.configure(state="disabled")

        # Progress bar
        self.linx_update_progressbar = ctk.CTkProgressBar(self.update_action_frame)
        self.linx_update_progressbar.grid(row=4, column=0, padx=15, pady=(5, 5), sticky="ew")
        self.linx_update_progressbar.set(0)

        self.linx_update_status_label = ctk.CTkLabel(self.update_action_frame, text="Pronto para atualizar.", anchor="w")
        self.linx_update_status_label.grid(row=5, column=0, padx=15, pady=(0, 5), sticky="w")


    def build_services_ui(self):
        # Clear existing rows first
        for widget in self.services_list_container.winfo_children():
            widget.destroy()

        self.service_status_labels.clear()
        self.service_action_buttons.clear()

        # Load current configured service names
        c = self.app_config
        services = [
            ("dfe", c.get("linx_service_dfe", "DFeServico")),
            ("datasnap", c.get("linx_service_datasnap", "RedirecionaDatasnap")),
            ("3camadas", c.get("linx_service_3camadas", "VerificaServer3Camadas")),
            ("integrador", c.get("linx_service_integrador", "dmLDIServer"))
        ]

        for i, (key, s_name) in enumerate(services):
            # Display name label
            lbl_name = ctk.CTkLabel(self.services_list_container, text=s_name, font=ctk.CTkFont(weight="bold", size=12), anchor="w")
            lbl_name.grid(row=i, column=0, padx=5, pady=10, sticky="w")

            # Status Badge Label
            lbl_status = ctk.CTkLabel(self.services_list_container, text="CONSULTANDO...", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#7f8c8d", text_color="white", corner_radius=6, height=24)
            lbl_status.grid(row=i, column=1, padx=5, pady=10, sticky="ew")
            self.service_status_labels[key] = lbl_status

            # Toggle button
            btn_action = ctk.CTkButton(self.services_list_container, text="...", width=70, font=ctk.CTkFont(size=11, weight="bold"), height=24)
            btn_action.grid(row=i, column=2, padx=5, pady=10)
            self.service_action_buttons[key] = btn_action


    def refresh_linx_services(self):
        """Launches a background thread to check the status of all three services."""
        self.build_services_ui()
        self.refresh_services_btn.configure(state="disabled", text="Consultando...")
        for key, lbl in self.service_status_labels.items():
            lbl.configure(text="CONSULTANDO...", fg_color="#7f8c8d")
        for btn in self.service_action_buttons.values():
            btn.configure(state="disabled", text="...")
            
        threading.Thread(target=self._refresh_services_thread, daemon=True).start()


    def _refresh_services_thread(self):
        c = self.app_config
        services = {
            "dfe": c.get("linx_service_dfe", "DFeServico"),
            "datasnap": c.get("linx_service_datasnap", "RedirecionaDatasnap"),
            "3camadas": c.get("linx_service_3camadas", "VerificaServer3Camadas"),
            "integrador": c.get("linx_service_integrador", "dmLDIServer")
        }
        
        statuses = {}
        for key, s_name in services.items():
            statuses[key] = self.query_service_status(s_name)

        self.after(0, lambda: self.on_services_refreshed(statuses))


    def on_services_refreshed(self, statuses):
        self.refresh_services_btn.configure(state="normal", text="Atualizar Status")
        
        for key, status_val in statuses.items():
            lbl = self.service_status_labels.get(key)
            btn = self.service_action_buttons.get(key)
            if not lbl or not btn:
                continue

            if status_val == "ONLINE":
                lbl.configure(text="ONLINE", fg_color="#27ae60")
                btn.configure(state="normal", text="Parar", fg_color="#c0392b", hover_color="#e74c3c", 
                              command=lambda k=key: self.trigger_service_toggle(k, "stop"))
            elif status_val == "OFFLINE":
                lbl.configure(text="OFFLINE", fg_color="#c0392b")
                btn.configure(state="normal", text="Iniciar", fg_color="#27ae60", hover_color="#2ecc71", 
                              command=lambda k=key: self.trigger_service_toggle(k, "start"))
            elif status_val == "INDISPONIVEL":
                lbl.configure(text="APENAS WINDOWS", fg_color="#7f8c8d")
                btn.configure(state="disabled", text="Indisponível")
            else:
                lbl.configure(text="INEXISTENTE", fg_color="#7f8c8d")
                btn.configure(state="disabled", text="-")


    def query_service_status(self, service_name):
        if platform.system() != "Windows":
            return "INDISPONIVEL"

        import subprocess
        try:
            # Query service using sc
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                creationflags=0x08000000 # CREATE_NO_WINDOW
            )
            stdout = result.stdout or ""
            stdout_upper = stdout.upper()
            
            # Suporta diferentes idiomas do Windows (Inglês: STATE, Português/Espanhol: ESTADO, Alemão: STATUS, etc.)
            has_state_info = any(term in stdout_upper for term in ["STATE", "ESTADO", "STATUS", "STATO", "ETAT"])
            
            if has_state_info:
                if "RUNNING" in stdout_upper or "4  RUNNING" in stdout_upper:
                    return "ONLINE"
                elif "STOPPED" in stdout_upper or "1  STOPPED" in stdout_upper:
                    return "OFFLINE"
            
            # Validação caso o serviço não exista (erro 1060 em inglês/português)
            if "1060" in stdout_upper or "DOES NOT EXIST" in stdout_upper or "NAO EXISTE" in stdout_upper or "NÃO EXISTE" in stdout_upper:
                return "INEXISTENTE"
                
            return "OFFLINE"
        except Exception:
            return "DESCONHECIDO"


    def trigger_service_toggle(self, key, action):
        c = self.app_config
        s_name = ""
        if key == "dfe":
            s_name = c.get("linx_service_dfe", "DFeServico")
        elif key == "datasnap":
            s_name = c.get("linx_service_datasnap", "RedirecionaDatasnap")
        elif key == "3camadas":
            s_name = c.get("linx_service_3camadas", "VerificaServer3Camadas")
        elif key == "integrador":
            s_name = c.get("linx_service_integrador", "dmLDIServer")

        lbl = self.service_status_labels.get(key)
        btn = self.service_action_buttons.get(key)
        if lbl and btn:
            lbl.configure(text="PROCESSANDO...", fg_color="#e67e22")
            btn.configure(state="disabled", text="...")

        threading.Thread(target=self._toggle_service_thread, args=(key, s_name, action), daemon=True).start()


    def _toggle_service_thread(self, key, s_name, action):
        if platform.system() != "Windows":
            # Simulate on Linux
            import time
            time.sleep(1.5)
            self.mock_service_states[s_name] = "ONLINE" if action == "start" else "OFFLINE"
        else:
            import subprocess
            # Use 'sc' or 'net' to start or stop service (elevated is best, but sc works)
            try:
                subprocess.run(
                    ["sc", action, s_name],
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000
                )
                # Wait 2 seconds for state transition
                import time
                time.sleep(2.0)
            except Exception:
                pass
        
        # Query status again
        status_val = self.query_service_status(s_name)
        self.after(0, lambda: self.on_service_toggled(key, status_val))


    def on_service_toggled(self, key, status_val):
        # Refresh all service statuses
        self.refresh_linx_services()


    def stop_apollo_server_process(self):
        def run_stop():
            try:
                self.after(0, lambda: self.log_to_linx_update_console("Solicitação para encerrar processos do ApolloServer (*serverapp*)..."))
                if platform.system() == "Windows":
                    import subprocess
                    cmd = ["powershell", "-Command", "stop-process -name *serverapp* -Force"]
                    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                    if res.returncode == 0:
                        self.after(0, lambda: messagebox.showinfo("Sucesso", "Processos do ApolloServer (*serverapp*) encerrados com sucesso!"))
                        self.after(0, lambda: self.log_to_linx_update_console("Processos do ApolloServer (*serverapp*) encerrados com sucesso."))
                    else:
                        err_out = res.stderr.strip() or res.stdout.strip() or "Nenhum processo *serverapp* em execução."
                        self.after(0, lambda: messagebox.showinfo("Informação", f"Resultado do comando ApolloServer:\n{err_out}"))
                        self.after(0, lambda: self.log_to_linx_update_console(f"Resultado ApolloServer: {err_out}"))
                else:
                    self.after(0, lambda: messagebox.showinfo("Simulação (Linux)", "Comando executado (Simulado):\npowershell stop-process -name *serverapp*"))
                    self.after(0, lambda: self.log_to_linx_update_console("[Linux SIMULADO] Comando enviado: powershell stop-process -name *serverapp*"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao fechar ApolloServer:\n{err_msg}"))
                self.after(0, lambda: self.log_to_linx_update_console(f"Erro ao fechar ApolloServer: {err_msg}"))

        threading.Thread(target=run_stop, daemon=True).start()


    def stop_process_by_regex(self, pattern=None):
        if not pattern:
            pattern = self.linx_kill_pattern_entry.get().strip() if hasattr(self, 'linx_kill_pattern_entry') else "wsContabil"
        
        if not pattern:
            messagebox.showwarning("Aviso", "Por favor, informe o nome ou padrão Regex do processo a encerrar.")
            return

        def run_kill():
            try:
                self.after(0, lambda: self.log_to_linx_update_console(f"Solicitação para encerrar processos via Regex/Nome: '{pattern}'..."))
                if platform.system() == "Windows":
                    import subprocess
                    safe_pattern = pattern.replace("'", "''")
                    ps_cmd = f"Get-Process | Where-Object {{ $_.ProcessName -match '{safe_pattern}' -or $_.Name -like '*{safe_pattern}*' }} | Stop-Process -Force"
                    cmd = ["powershell", "-Command", ps_cmd]
                    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                    if res.returncode == 0:
                        self.after(0, lambda: messagebox.showinfo("Sucesso", f"Processo(s) correspondente(s) a '{pattern}' encerrado(s) com sucesso!"))
                        self.after(0, lambda: self.log_to_linx_update_console(f"Processo(s) correspondente(s) a '{pattern}' encerrado(s) com sucesso."))
                    else:
                        err_out = res.stderr.strip() or res.stdout.strip() or f"Nenhum processo correspondente a '{pattern}' em execução."
                        self.after(0, lambda: messagebox.showinfo("Informação", f"Resultado do encerramento ({pattern}):\n{err_out}"))
                        self.after(0, lambda: self.log_to_linx_update_console(f"Resultado do encerramento ({pattern}): {err_out}"))
                else:
                    self.after(0, lambda: messagebox.showinfo("Simulação (Linux)", f"Comando executado (Simulado):\npowershell Get-Process | Where-Object {{ $_.ProcessName -match '{pattern}' }} | Stop-Process -Force"))
                    self.after(0, lambda: self.log_to_linx_update_console(f"[Linux SIMULADO] Encerrando processos por padrão Regex: '{pattern}'"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao fechar processo ({pattern}):\n{err_msg}"))
                self.after(0, lambda: self.log_to_linx_update_console(f"Erro ao fechar processo ({pattern}): {err_msg}"))

        threading.Thread(target=run_kill, daemon=True).start()


    def setup_tab_linx_settings(self):
        tab = self.frame_linx_settings
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        # Scrollable Settings Container
        self.linx_settings_scroll = ctk.CTkScrollableFrame(tab, label_text="Editar Parâmetros Linx (config.json)")
        self.linx_settings_scroll.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.linx_settings_scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.linx_settings_scroll, text="Templates de URL de Download (HTTP)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(self.linx_settings_scroll, text="Delphi (Download Padrão) URL Template:", anchor="w").grid(row=1, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_delphi_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_delphi_entry.grid(row=2, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="3 Camadas - Server URL Template:", anchor="w").grid(row=3, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_server_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_server_entry.grid(row=4, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="3 Camadas - Client URL Template:", anchor="w").grid(row=5, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_client_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_client_entry.grid(row=6, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="Instalador Web URL Template:", anchor="w").grid(row=7, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_web_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_web_entry.grid(row=8, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="Comissões Delphi URL Template:", anchor="w").grid(row=9, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_comissoes_delphi_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_comissoes_delphi_entry.grid(row=10, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="Comissões Client URL Template:", anchor="w").grid(row=11, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_comissoes_client_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_comissoes_client_entry.grid(row=12, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="Apoio URL Template:", anchor="w").grid(row=13, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_apoio_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_apoio_entry.grid(row=14, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.linx_settings_scroll, text="Linx DMS Integrador URL Template:", anchor="w").grid(row=141, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_url_integrador_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="https://...")
        self.linx_url_integrador_entry.grid(row=142, column=0, padx=10, pady=2, sticky="ew")

        # --- SECTION 2: SERVICES CONFIG ---
        ctk.CTkLabel(self.linx_settings_scroll, text="Nomes de Serviços Windows", font=ctk.CTkFont(size=14, weight="bold")).grid(row=15, column=0, padx=10, pady=(15, 5), sticky="w")

        ctk.CTkLabel(self.linx_settings_scroll, text="Serviço DFe (DFeServico):", anchor="w").grid(row=16, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_service_dfe_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="DFeServico")
        self.linx_service_dfe_entry.grid(row=17, column=0, padx=10, pady=2, sticky="ew")
        self.linx_service_dfe_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_service_dfe_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        ctk.CTkLabel(self.linx_settings_scroll, text="Serviço DataSnap (RedirecionaDatasnap):", anchor="w").grid(row=18, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_service_datasnap_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="RedirecionaDatasnap")
        self.linx_service_datasnap_entry.grid(row=19, column=0, padx=10, pady=2, sticky="ew")
        self.linx_service_datasnap_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_service_datasnap_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        ctk.CTkLabel(self.linx_settings_scroll, text="Serviço 3 Camadas Server (VerificaServer3Camadas):", anchor="w").grid(row=20, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_service_3camadas_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="VerificaServer3Camadas")
        self.linx_service_3camadas_entry.grid(row=21, column=0, padx=10, pady=2, sticky="ew")
        self.linx_service_3camadas_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_service_3camadas_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        ctk.CTkLabel(self.linx_settings_scroll, text="Serviço Integrador (dmLDIServer):", anchor="w").grid(row=211, column=0, padx=10, pady=(5, 0), sticky="w")
        self.linx_service_integrador_entry = ctk.CTkEntry(self.linx_settings_scroll, placeholder_text="dmLDIServer")
        self.linx_service_integrador_entry.grid(row=212, column=0, padx=10, pady=2, sticky="ew")
        self.linx_service_integrador_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_service_integrador_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        # --- SECTION 3: DIRECTORIES CONFIG ---
        ctk.CTkLabel(self.linx_settings_scroll, text="Diretórios de Atualização", font=ctk.CTkFont(size=14, weight="bold")).grid(row=22, column=0, padx=10, pady=(15, 5), sticky="w")

        ctk.CTkLabel(self.linx_settings_scroll, text="Pasta Apollo/Atualiza (Arquivos Normais):", anchor="w").grid(row=23, column=0, padx=10, pady=(5, 0), sticky="w")
        path_normal_frame = ctk.CTkFrame(self.linx_settings_scroll, fg_color="transparent")
        path_normal_frame.grid(row=24, column=0, padx=10, pady=2, sticky="ew")
        path_normal_frame.grid_columnconfigure(0, weight=1)
        self.linx_path_normal_entry = ctk.CTkEntry(path_normal_frame)
        self.linx_path_normal_entry.grid(row=0, column=0, sticky="ew")
        self.linx_path_normal_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_path_normal_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_normal_frame, text="...", width=30, command=lambda: self.browse_directory(self.linx_path_normal_entry)).grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(self.linx_settings_scroll, text="Pasta 3Camadas (Server 3 Camadas):", anchor="w").grid(row=25, column=0, padx=10, pady=(5, 0), sticky="w")
        path_server_frame = ctk.CTkFrame(self.linx_settings_scroll, fg_color="transparent")
        path_server_frame.grid(row=26, column=0, padx=10, pady=2, sticky="ew")
        path_server_frame.grid_columnconfigure(0, weight=1)
        self.linx_path_server_entry = ctk.CTkEntry(path_server_frame)
        self.linx_path_server_entry.grid(row=0, column=0, sticky="ew")
        self.linx_path_server_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_path_server_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_server_frame, text="...", width=30, command=lambda: self.browse_directory(self.linx_path_server_entry)).grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(self.linx_settings_scroll, text="Pasta 3Camadas/Atualiza (Client 3 Camadas):", anchor="w").grid(row=27, column=0, padx=10, pady=(5, 0), sticky="w")
        path_client_frame = ctk.CTkFrame(self.linx_settings_scroll, fg_color="transparent")
        path_client_frame.grid(row=28, column=0, padx=10, pady=2, sticky="ew")
        path_client_frame.grid_columnconfigure(0, weight=1)
        self.linx_path_client_entry = ctk.CTkEntry(path_client_frame)
        self.linx_path_client_entry.grid(row=0, column=0, sticky="ew")
        self.linx_path_client_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.linx_path_client_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_client_frame, text="...", width=30, command=lambda: self.browse_directory(self.linx_path_client_entry)).grid(row=0, column=1, padx=(5, 0))

        # --- SECTION 4: APPEARANCE CONFIG ---
        ctk.CTkLabel(self.linx_settings_scroll, text="Aparência Visual", font=ctk.CTkFont(size=14, weight="bold")).grid(row=29, column=0, padx=10, pady=(15, 5), sticky="w")
        self.linx_settings_appearance_menu = ctk.CTkOptionMenu(self.linx_settings_scroll, values=["Dark", "Light", "System"], command=lambda v: self.save_ui_to_config())
        self.linx_settings_appearance_menu.grid(row=30, column=0, padx=10, pady=5, sticky="w")

        # Save Button Frame
        save_frame = ctk.CTkFrame(tab, fg_color="transparent")
        save_frame.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        save_frame.grid_columnconfigure(0, weight=1)

        self.save_linx_settings_btn = ctk.CTkButton(save_frame, text="Salvar Configurações Linx", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.save_settings_manually)
        self.save_linx_settings_btn.grid(row=0, column=0, sticky="ew")


    def log_to_linx_console(self, message):
        """Append a message to the Linx log console and scroll to the bottom."""
        self.linx_console_log.configure(state="normal")
        self.linx_console_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.linx_console_log.configure(state="disabled")
        self.linx_console_log.see("end")


    def set_linx_download_inputs_state(self, state):
        self.linx_package_menu.configure(state=state)
        self.linx_version_entry.configure(state=state)
        self.linx_path_entry.configure(state=state)
        self.linx_dl_delphi_check.configure(state=state)
        self.linx_dl_server_check.configure(state=state)
        self.linx_dl_client_check.configure(state=state)
        self.linx_dl_web_check.configure(state=state)
        self.linx_dl_comissoes_check.configure(state=state)
        self.linx_dl_apoio_trocafornec_check.configure(state=state)
        self.linx_dl_apoio_trocaserie_check.configure(state=state)
        self.linx_dl_apoio_verificadiaria_check.configure(state=state)
        self.linx_dl_integrador_check.configure(state=state)
        self.linx_backup_apollo_check.configure(state=state)


    def show_linx_running_buttons(self):
        self.linx_start_dl_btn.grid_forget()
        self.linx_pause_dl_btn.grid(row=1, column=1, padx=10, pady=(5, 2), sticky="ew")
        self.linx_cancel_dl_btn.grid(row=2, column=1, padx=10, pady=(2, 5), sticky="ew")
        self.linx_pause_dl_btn.configure(text="Pausar")


    def show_linx_idle_buttons(self):
        self.linx_pause_dl_btn.grid_forget()
        self.linx_cancel_dl_btn.grid_forget()
        self.linx_start_dl_btn.grid(row=1, column=1, rowspan=2, padx=10, pady=5, sticky="nsew")


    def toggle_linx_pause_download(self):
        if self.linx_download_paused:
            self.linx_download_paused = False
            self.linx_pause_dl_btn.configure(text="Pausar")
            self.log_to_linx_console("Processo retomado.")
            self.linx_dl_status_label.configure(text="Retomando download...")
        else:
            self.linx_download_paused = True
            self.linx_pause_dl_btn.configure(text="Retomar")
            self.log_to_linx_console("Processo pausado. Aguardando...")
            self.linx_dl_status_label.configure(text="Pausado.")


    def cancel_linx_download(self):
        self.linx_download_cancelled = True
        self.linx_download_paused = False
        self.log_to_linx_console("Solicitação de cancelamento enviada. Aguardando...")
        self.linx_dl_status_label.configure(text="Cancelando...")


    def start_linx_download_process(self):
        # Save state
        self.save_ui_to_config()

        # Validations
        package = self.linx_package_menu.get()
        version = self.linx_version_entry.get().strip()
        path = self.linx_path_entry.get().strip()

        if not version:
            messagebox.showerror("Erro", "Por favor, digite a versão desejada (ex: v5.19).")
            return
        if not path:
            messagebox.showerror("Erro", "Por favor, digite ou selecione o diretório de destino.")
            return

        # Check if at least one checkbox is checked
        if not (self.linx_dl_delphi_var.get() or self.linx_dl_server_var.get() or 
                self.linx_dl_client_var.get() or self.linx_dl_web_var.get() or
                self.linx_dl_comissoes_var.get() or self.linx_dl_apoio_trocafornec_var.get() or
                self.linx_dl_apoio_trocaserie_var.get() or self.linx_dl_apoio_verificadiaria_var.get()):
            messagebox.showerror("Erro", "Selecione pelo menos uma opção de download.")
            return

        # Setup state
        self.linx_download_paused = False
        self.linx_download_cancelled = False
        self.linx_current_downloading_file = None

        # Lock UI
        self.set_navigation_state("disabled")
        self.set_linx_download_inputs_state("disabled")
        self.show_linx_running_buttons()

        self.linx_console_log.configure(state="normal")
        self.linx_console_log.delete("1.0", "end")
        self.linx_console_log.configure(state="disabled")
        self.linx_dl_progressbar.set(0)

        # Launch Thread
        threading.Thread(target=self._linx_download_process_thread, args=(package, version, path), daemon=True).start()


    def _linx_download_process_thread(self, package, version, path):
        def log(msg):
            self.after(0, lambda: self.log_to_linx_console(msg))
        def status(txt):
            self.after(0, lambda: self.linx_dl_status_label.configure(text=txt))

        def check_pause_cancel():
            import time
            while self.linx_download_paused:
                time.sleep(0.1)
                if self.linx_download_cancelled:
                    raise Exception("Processo cancelado pelo usuário.")
            if self.linx_download_cancelled:
                raise Exception("Processo cancelado pelo usuário.")

        def progress_callback(dl_bytes, total_bytes):
            check_pause_cancel()
            if total_bytes > 0:
                pct = dl_bytes / total_bytes
                self.after(0, lambda: self.linx_dl_progressbar.set(pct))

        try:
            # Prepend 'v' to version automatically if missing
            version_with_v = version if version.startswith("v") else "v" + version

            log("--- INICIANDO PROCESSO DOWNLOAD LINX ---")
            log(f"Pacote selecionado: {package}")
            log(f"Versão: {version_with_v}")
            log(f"Pasta de downloads: {os.path.abspath(path)}")
            os.makedirs(path, exist_ok=True)

            c = self.app_config
            downloads_to_make = []

            # Add tasks based on variables
            if self.linx_dl_delphi_var.get():
                template = c.get("linx_url_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_delphi_template"]
                url = template.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}.zip"
                downloads_to_make.append(("Delphi (Padrão)", url, filename))

            if self.linx_dl_server_var.get():
                template = c.get("linx_url_server_template", "").strip() or config.DEFAULT_CONFIG["linx_url_server_template"]
                url = template.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}_3Camadas_Server.zip"
                downloads_to_make.append(("3 Camadas Server", url, filename))

            if self.linx_dl_client_var.get():
                template = c.get("linx_url_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_client_template"]
                url = template.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}_3Camadas_Client.zip"
                downloads_to_make.append(("3 Camadas Client", url, filename))

            if self.linx_dl_web_var.get():
                template = c.get("linx_url_web_template", "").strip() or config.DEFAULT_CONFIG["linx_url_web_template"]
                url = template.replace("{package}", package).replace("{version}", version_with_v)
                filename = "LinxDMS.zip"
                downloads_to_make.append(("Instalador Web", url, filename))

            if self.linx_dl_integrador_var.get():
                template = c.get("linx_url_integrador_template", "").strip() or config.DEFAULT_CONFIG["linx_url_integrador_template"]
                url = template.replace("{package}", package).replace("{version}", version_with_v)
                filename = "LinxDMSIntegrador.zip"
                downloads_to_make.append(("Linx DMS Integrador", url, filename))

            # Add Comissões downloads if selected
            if self.linx_dl_comissoes_var.get():
                if self.linx_dl_delphi_var.get():
                    template = c.get("linx_url_comissoes_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_delphi_template"]
                    url = template.replace("{version}", version_with_v)
                    downloads_to_make.append(("Comissões Delphi", url, "LinxDMSComissoes.zip"))
                if self.linx_dl_client_var.get():
                    template = c.get("linx_url_comissoes_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_client_template"]
                    url = template.replace("{version}", version_with_v)
                    downloads_to_make.append(("Comissões Client", url, "LinxDMSComissoesClient.zip"))
                if self.linx_dl_server_var.get():
                    log("Aviso: Comissões não possui pacote de Server. Ignorando download Server para Comissões.")

            # Add Apoio downloads if selected
            apoio_modules = []
            if self.linx_dl_apoio_trocafornec_var.get():
                apoio_modules.append(("Troca Fornecedor", "TrocaFornec"))
            if self.linx_dl_apoio_trocaserie_var.get():
                apoio_modules.append(("Troca Série Transmissão", "TrocaSerieTran"))
            if self.linx_dl_apoio_verificadiaria_var.get():
                apoio_modules.append(("Verifica Composição Diária", "VerificaComposicaoDiaria"))

            for label, base_filename in apoio_modules:
                template = c.get("linx_url_apoio_template", "").strip() or config.DEFAULT_CONFIG["linx_url_apoio_template"]
                if self.linx_dl_delphi_var.get():
                    url = template.replace("{version}", version_with_v).replace("{filename}", base_filename)
                    downloads_to_make.append((f"{label} Delphi", url, f"{base_filename}.zip"))
                if self.linx_dl_client_var.get():
                    client_filename = f"{base_filename}Client"
                    url = template.replace("{version}", version_with_v).replace("{filename}", client_filename)
                    downloads_to_make.append((f"{label} Client", url, f"{client_filename}.zip"))
                if self.linx_dl_server_var.get():
                    log(f"Aviso: {label} não possui pacote de Server. Ignorando download Server para {label}.")

            success_count = 0
            for label, url, filename in downloads_to_make:
                check_pause_cancel()
                dest_file = os.path.join(path, filename)
                log(f"Baixando {label}...")
                log(f"URL: {url}")
                status(f"Baixando {filename}...")
                self.after(0, lambda: self.linx_dl_progressbar.set(0))

                self.linx_current_downloading_file = dest_file
                utils.download_http_file(url, dest_file, progress_callback, check_pause_cancel)
                self.linx_current_downloading_file = None

                log(f"Download concluído: {filename}")
                self.after(0, lambda: self.linx_dl_progressbar.set(1.0))
                success_count += 1

            status("Download Linx Concluído.")
            log(f"Sucesso! {success_count} de {len(downloads_to_make)} downloads concluídos.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", f"Processo finalizado com sucesso! {success_count} arquivos baixados em:\n{path}"))

        except Exception as e:
            status("Processo interrompido.")
            err_msg = str(e)
            log(f"ERRO: {err_msg}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Processo interrompido devido a erro:\n{err_msg}"))

        finally:
            self.after(0, lambda: self.set_navigation_state("normal"))
            self.after(0, lambda: self.set_linx_download_inputs_state("normal"))
            self.after(0, lambda: self.show_linx_idle_buttons())


    def start_linx_update_process(self):
        if self.linx_updating:
            return
        
        # Save config
        self.save_ui_to_config()

        self.linx_updating = True
        self.linx_update_cancelled = False
        
        # Lock navigation
        self.set_navigation_state("disabled")
        self.linx_start_update_btn.configure(state="disabled", text="Atualizando...")
        
        self.linx_update_console_log.configure(state="normal")
        self.linx_update_console_log.delete("1.0", "end")
        self.linx_update_console_log.configure(state="disabled")
        self.linx_update_progressbar.set(0)

        # Launch Thread
        threading.Thread(target=self._linx_update_process_thread, daemon=True).start()


    def _linx_update_process_thread(self):
        import zipfile
        
        def log(msg):
            self.after(0, lambda: self.log_to_linx_update_console(msg))
        def status(txt):
            self.after(0, lambda: self.linx_update_status_label.configure(text=txt))
        def progress(val):
            self.after(0, lambda: self.linx_update_progressbar.set(val))

        try:
            c = self.app_config
            download_dir = self.linx_path_entry.get().strip()
            
            # Paths destinations
            dest_normal = c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_normal_linux", "./Apollo_Atualiza")
            dest_server = c.get("linx_path_server_win", "C:\\3Camadas") if self.os_type == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
            dest_client = c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_client_linux", "./3Camadas_Atualiza")

            log("--- INICIANDO PROCESSO DE ATUALIZAÇÃO LINX ---")
            log(f"Pasta de downloads de origem: {os.path.abspath(download_dir)}")
            log(f"Destino Delphi/Normais: {os.path.abspath(dest_normal)}")
            log(f"Destino 3 Camadas Server: {os.path.abspath(dest_server)}")
            log(f"Destino 3 Camadas Client: {os.path.abspath(dest_client)}")

            if not os.path.exists(download_dir):
                raise Exception(f"Diretório de downloads de origem não existe: {download_dir}")

            # Scan files
            zip_files = [f for f in os.listdir(download_dir) if f.lower().endswith(".zip")]
            if not zip_files:
                log("Nenhum arquivo .zip encontrado na pasta de download.")
                status("Nenhum arquivo zip para atualizar.")
                progress(1.0)
                return

            total_zips = len(zip_files)
            log(f"Encontrados {total_zips} arquivos .zip para processar.")

            # Encerrar processos em execução (ex: wsContabil) para evitar bloqueio de arquivos
            kill_pat = c.get("linx_kill_process_pattern", "wsContabil").strip()
            if kill_pat:
                log(f"Verificando e encerrando processos ativos correspondentes a '{kill_pat}'...")
                self.stop_process_by_regex(kill_pat)

            # Realiza backup dos executáveis e DLLs da pasta C:\Apollo\atualiza somente antes da descompactação
            if c.get("linx_backup_apollo", False):
                status("Fazendo backup do Apollo (EXE/DLL)...")
                log("\n--- INICIANDO BACKUP AUTOMÁTICO DO APOLLO (EXE E DLL) ---")
                parent_apollo = os.path.dirname(dest_normal.rstrip("\\/"))
                date_str = datetime.now().strftime("%d%m%Y")
                backup_folder_name = f"backup_{date_str}"
                backup_dir = os.path.join(parent_apollo if parent_apollo else dest_normal, backup_folder_name)
                log(f"Diretório Apollo (origem): {os.path.abspath(dest_normal)}")
                log(f"Diretório de backup (destino): {os.path.abspath(backup_dir)}")
                backup_ok = utils.backup_apollo_executables_and_dlls(dest_normal, backup_dir, log)
                if backup_ok:
                    log(f"Backup dos arquivos EXE e DLL do Apollo realizado com sucesso em '{backup_folder_name}'.")
                else:
                    log("Aviso: Falha ao realizar backup do Apollo ou nenhum arquivo EXE/DLL encontrado.")
                log("---------------------------------------------------------\n")

            for index, zip_name in enumerate(zip_files):
                zip_path = os.path.join(download_dir, zip_name)
                log(f"\n[{index+1}/{total_zips}] Processando: {zip_name}")
                status(f"Descompactando {zip_name}...")
                progress((index) / total_zips)

                # Temp dir for extraction
                temp_extract = os.path.join(download_dir, "temp_extract_" + os.path.splitext(zip_name)[0])
                os.makedirs(temp_extract, exist_ok=True)

                # Extract
                log(f"Descompactando {zip_name} em pasta temporária...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)
                log("Descompactação concluída.")

                # Identify package type based on name
                name_lower = zip_name.lower()
                
                # Check for 3Camadas Server
                if "3camadas_server" in name_lower or "_server.zip" in name_lower or "server_3camadas" in name_lower:
                    log(f"Identificado como: 3 Camadas Server. Destino: {dest_server}")
                    status("Atualizando 3 Camadas Server...")
                    utils.copy_dir_recursive(temp_extract, dest_server, log)
                    log(f"Sucesso! Conteúdo copiado para {dest_server}")
                
                # Check for 3Camadas Client
                elif "3camadas_client" in name_lower or "_client.zip" in name_lower or "client_3camadas" in name_lower:
                    log(f"Identificado como: 3 Camadas Client. Destino: {dest_client}")
                    status("Atualizando 3 Camadas Client...")
                    utils.copy_dir_recursive(temp_extract, dest_client, log)
                    log(f"Sucesso! Conteúdo copiado para {dest_client}")
                
                # Check for Instalador Web
                elif "linxdms.zip" == name_lower or ("linxdms" in name_lower and "comissoes" not in name_lower and "apoio" not in name_lower and "evolutivo" not in name_lower and "3camadas" not in name_lower):
                    log("Identificado como: Instalador Web (LinxDMS Web). Procurando instalador...")
                    # Search for msi or exe
                    installers = []
                    for root, dirs, files in os.walk(temp_extract):
                        for f in files:
                            if f.lower().endswith(".msi") or f.lower().endswith(".exe"):
                                installers.append(os.path.join(root, f))
                    
                    if installers:
                        # Select first installer and run
                        inst_path = installers[0]
                        log(f"Executável de instalação encontrado: {os.path.basename(inst_path)}")
                        status(f"Executando instalador {os.path.basename(inst_path)}...")
                        log("Iniciando execução elevada como Administrador...")
                        success = utils.execute_script_as_admin(inst_path, log)
                        if success:
                            log("Instalador Web finalizado com sucesso.")
                        else:
                            log("Aviso: Falha ou cancelamento na execução do instalador Web.")
                    else:
                        log("Nenhum instalador (.msi ou .exe) encontrado dentro do zip do Instalador Web.")
                        # Move files normally as fallback
                        log(f"Movendo conteúdo extraído para pasta de atualização Delphi: {dest_normal}")
                        utils.copy_dir_recursive(temp_extract, dest_normal, log)

                # Check for Linx DMS Integrador
                elif "linxdmsintegrador.zip" == name_lower or "integrador" in name_lower:
                    log("Identificado como: Linx DMS Integrador. Procurando instalador...")
                    # Search for msi or exe
                    installers = []
                    for root, dirs, files in os.walk(temp_extract):
                        for f in files:
                            if f.lower().endswith(".msi") or f.lower().endswith(".exe"):
                                installers.append(os.path.join(root, f))
                    
                    if installers:
                        inst_path = installers[0]
                        log(f"Executável de instalação encontrado: {os.path.basename(inst_path)}")
                        status(f"Executando instalador {os.path.basename(inst_path)}...")
                        log("Iniciando execução elevada como Administrador...")
                        success = utils.execute_script_as_admin(inst_path, log)
                        if success:
                            log("Instalador Integrador finalizado com sucesso.")
                        else:
                            log("Aviso: Falha ou cancelamento na execução do instalador Integrador.")
                    else:
                        log("Nenhum instalador (.msi ou .exe) encontrado dentro do zip do Integrador.")
                        # Move files normally as fallback
                        log(f"Movendo conteúdo extraído para pasta de atualização Delphi: {dest_normal}")
                        utils.copy_dir_recursive(temp_extract, dest_normal, log)

                # Default: normal evolutionary packages, comissoes or apoio
                else:
                    log(f"Identificado como: Pacote Normal/Comissões/Apoio. Destino: {dest_normal}")
                    status("Atualizando arquivos normais...")
                    utils.copy_dir_recursive(temp_extract, dest_normal, log)
                    log(f"Sucesso! Conteúdo copiado para {dest_normal}")

                # Clean temp extract folder
                try:
                    import shutil
                    shutil.rmtree(temp_extract)
                    log("Pasta temporária de extração limpa.")
                except Exception as e:
                    log(f"Aviso ao remover pasta temporária: {str(e)}")

            # Exclusão dos arquivos zipados da pasta de atualização de origem
            log("\n--- EXCLUINDO ARQUIVOS COMPACTADOS (.ZIP) DE ORIGEM ---")
            status("Excluindo arquivos zip baixados...")
            deleted_zips_count = 0
            for z_file in zip_files:
                z_full_path = os.path.join(download_dir, z_file)
                if os.path.exists(z_full_path):
                    try:
                        os.remove(z_full_path)
                        log(f"Arquivo zip removido: {z_file}")
                        deleted_zips_count += 1
                    except Exception as e_rm:
                        log(f"Aviso ao remover zip {z_file}: {str(e_rm)}")
            log(f"Limpeza concluída. {deleted_zips_count} arquivos .zip removidos da pasta de origem.")

            log("\n--- PROCESSO DE ATUALIZAÇÃO CONCLUÍDO COM SUCESSO ---")
            status("Atualização Concluída.")
            progress(1.0)
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Atualização concluída com sucesso! Todos os pacotes Linx foram descompactados e aplicados nos destinos correspondentes."))

        except Exception as e:
            status("Processo abortado.")
            err_msg = str(e)
            log(f"ERRO CRÍTICO: {err_msg}")
            self.after(0, lambda: messagebox.showerror("Erro na Atualização", f"Ocorreu um erro no processo de atualização:\n{err_msg}"))

        finally:
            self.linx_updating = False
            self.after(0, lambda: self.set_navigation_state("normal"))
            self.after(0, lambda: self.linx_start_update_btn.configure(state="normal", text="Iniciar Atualização"))


    def log_to_linx_update_console(self, message):
        self.linx_update_console_log.configure(state="normal")
        self.linx_update_console_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.linx_update_console_log.configure(state="disabled")
        self.linx_update_console_log.see("end")


    def setup_tab_linx_utilities(self):
        tab = self.frame_linx_utilities
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_rowconfigure(3, weight=1)
        tab.grid_rowconfigure(4, weight=1)

        # Title
        ctk.CTkLabel(tab, text="Utilitários e Manutenção Linx", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkLabel(tab, text="Ferramentas auxiliares para gerenciamento, pesquisa, limpeza de arquivos e reinício de servidores Linx.", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Cleanup card
        cleanup_frame = ctk.CTkFrame(tab)
        cleanup_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        cleanup_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cleanup_frame, text="Limpeza de Executáveis e DLLs do Linx", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        details_text = (
            "Esta ferramenta permite listar, pesquisar e excluir arquivos executáveis (.exe) e bibliotecas (.dll)\n"
            "nas pastas do Linx (Apollo/Atualiza, 3Camadas Server, ou 3Camadas Client).\n\n"
            "Quando arquivos estão abertos/travados, eles são renomeados pelo sistema com padrões como 'nome_data.exe'.\n"
            "Você pode utilizar filtros de texto comum, glob (ex: *2026*.dll) ou expressões regulares (regex) para pesquisar\n"
            "e marcar somente os arquivos desejados para a remoção definitiva."
        )
        ctk.CTkLabel(cleanup_frame, text=details_text, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.linx_cleanup_btn = ctk.CTkButton(cleanup_frame, text="Limpar Executáveis/DLLs Linx", font=ctk.CTkFont(size=13, weight="bold"), height=35, command=self.open_linx_cleanup_popup)
        self.linx_cleanup_btn.grid(row=2, column=0, padx=15, pady=(0, 20), sticky="w")

        # Extension cleanup card
        ext_frame = ctk.CTkFrame(tab)
        ext_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        ext_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ext_frame, text="Limpeza de Arquivos por Extensão (Linx)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        ext_details = (
            "Esta ferramenta permite pesquisar e excluir arquivos de qualquer extensão específica (ex: .log, .tmp, .zip)\n"
            "dentro dos diretórios do Linx ou outro diretório que você escolher.\n"
            "Você define a extensão a ser buscada, filtra os resultados e seleciona manualmente quais remover."
        )
        ctk.CTkLabel(ext_frame, text=ext_details, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.linx_ext_cleanup_btn = ctk.CTkButton(ext_frame, text="Limpar por Extensão Linx", font=ctk.CTkFont(size=13, weight="bold"), height=35, command=lambda: self.open_extension_cleanup_popup("linx"))
        self.linx_ext_cleanup_btn.grid(row=2, column=0, padx=15, pady=(0, 20), sticky="w")

        # Remote Reboot via PowerShell Card
        linx_ps_frame = ctk.CTkFrame(tab)
        linx_ps_frame.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        linx_ps_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(linx_ps_frame, text="Reinício de Servidores Remotos (PowerShell)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        linx_ps_details = (
            "Esta ferramenta permite enviar o comando PowerShell (`Restart-Computer`) para reiniciar servidores adjacentes do Linx.\n"
            "Permite forçar o reinício (-Force) encerrando sessões de usuários conectados e serviços ativos no servidor de destino."
        )
        ctk.CTkLabel(linx_ps_frame, text=linx_ps_details, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.linx_ps_reboot_btn = ctk.CTkButton(linx_ps_frame, text="Reiniciar Servidor Linx (PowerShell)", font=ctk.CTkFont(size=13, weight="bold"), height=35, command=lambda: self.open_powershell_restart_popup("linx"))
        self.linx_ps_reboot_btn.grid(row=2, column=0, padx=15, pady=(0, 20), sticky="w")



    def open_linx_cleanup_popup(self):
        """Abre uma janela pop-up modal para listar, pesquisar por glob/regex, e excluir arquivos exe/dll do Linx."""
        c = self.app_config

        # Create window
        popup = ctk.CTkToplevel(self)
        popup.title("Limpeza de Executáveis e DLLs - Linx DMS")
        screen_h = self.winfo_screenheight()
        target_h = min(620, max(440, screen_h - 120))
        popup.geometry(f"640x{target_h}")
        popup.minsize(520, 400)
        popup.grab_set()  # Make modal

        # Title labels
        ctk.CTkLabel(popup, text="Utilitário de Limpeza Linx", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Top Control Frame (Directory selection + Path details)
        top_ctrl = ctk.CTkFrame(popup)
        top_ctrl.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        top_ctrl.grid_columnconfigure(0, weight=1)
        top_ctrl.grid_columnconfigure(1, weight=3)
        top_ctrl.grid_columnconfigure(2, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_ctrl, text="Pasta Linx a Limpar:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        custom_path_var = ctk.StringVar(value="")

        # Directory resolution helper
        def get_resolved_path(dir_key):
            if dir_key == "C:\\Apollo":
                return "C:\\Apollo" if self.os_type == "Windows" else "./Apollo"
            elif dir_key == "C:\\3camadas":
                return "C:\\3camadas" if self.os_type == "Windows" else "./3Camadas"
            elif dir_key == "Outro Diretório...":
                return custom_path_var.get()
            return ""

        # OptionMenu selection
        dir_var = ctk.StringVar(value="C:\\Apollo")
        dir_label_path = ctk.CTkLabel(popup, text="Caminho: -", font=ctk.CTkFont(size=11, slant="italic"), anchor="w")
        dir_label_path.grid(row=2, column=0, padx=20, pady=(2, 8), sticky="w")

        # Search/Filter Frame
        filter_frame = ctk.CTkFrame(popup)
        filter_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(filter_frame, text="Pesquisa / Filtro (Glob/Regex):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        
        filter_entry_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_entry_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        filter_entry_frame.grid_columnconfigure(0, weight=1)

        filter_entry = ctk.CTkEntry(filter_entry_frame, placeholder_text="Ex: *2026*.dll ou ^DMS_.*\\.exe$")
        filter_entry.grid(row=0, column=0, sticky="ew")

        # Selection tracking dictionaries
        all_files_found = []
        file_checkboxes_widgets = []
        checkbox_selections = {} # Stores {filepath: BooleanVar}

        # Scroll frame for items list
        scroll_frame = ctk.CTkScrollableFrame(popup, label_text="Arquivos Encontrados (.exe / .dll)")
        scroll_frame.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        popup.grid_rowconfigure(4, weight=1)

        # Glob / Regex matching logic
        import fnmatch
        import re

        def matches_pattern(filename, pattern):
            if not pattern:
                return True
            pattern = pattern.strip()
            # 1. Glob matching (contains * or ?)
            if "*" in pattern or "?" in pattern:
                try:
                    return fnmatch.fnmatchcase(filename.lower(), pattern.lower())
                except Exception:
                    pass
            # 2. Regex matching
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                return bool(regex.search(filename))
            except Exception:
                pass
            # 3. Simple substring fallback
            return pattern.lower() in filename.lower()

        # Render list based on filter
        def populate_list():
            # Clear widgets inside scroll frame
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

            # Filter original files
            filtered_files = []
            for f in all_files_found:
                if matches_pattern(f, filter_text):
                    filtered_files.append(f)

            if not filtered_files:
                empty_lbl = ctk.CTkLabel(scroll_frame, text="Nenhum executável ou DLL corresponde à pesquisa.", font=ctk.CTkFont(slant="italic"))
                empty_lbl.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                file_checkboxes_widgets.append(empty_lbl)
                return

            for idx, filename in enumerate(filtered_files):
                full_path = os.path.join(target_path, filename)
                
                # Checkbox selection tracking
                if full_path not in checkbox_selections:
                    checkbox_selections[full_path] = ctk.BooleanVar(value=False)
                
                # Check stats
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
        # Browse Custom Dir button helper
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

            if os.path.exists(target_path):
                try:
                    for name in os.listdir(target_path):
                        if os.path.isfile(os.path.join(target_path, name)):
                            name_lower = name.lower()
                            if name_lower.endswith(".exe") or name_lower.endswith(".dll"):
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

        # UI Actions
        dir_menu = ctk.CTkOptionMenu(top_ctrl, variable=dir_var, values=["C:\\Apollo", "C:\\3camadas", "Outro Diretório..."], command=lambda v: scan_directory())
        dir_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        btn_browse = ctk.CTkButton(top_ctrl, text="Pesquisar...", width=95, command=browse_custom_dir)
        btn_browse.grid(row=0, column=2, padx=(0, 10), pady=5)

        # Buttons in filter entry frame
        btn_apply = ctk.CTkButton(filter_entry_frame, text="Filtrar", width=80, command=populate_list)
        btn_apply.grid(row=0, column=1, padx=(5, 0))

        btn_clear = ctk.CTkButton(filter_entry_frame, text="Limpar", width=80, fg_color="transparent", border_width=1, command=lambda: [filter_entry.delete(0, "end"), populate_list()])
        btn_clear.grid(row=0, column=2, padx=(5, 0))

        # Selection Control Row (Marcar/Desmarcar Filtrados)
        sel_ctrl_frame = ctk.CTkFrame(popup, fg_color="transparent")
        sel_ctrl_frame.grid(row=5, column=0, padx=20, pady=2, sticky="ew")
        sel_ctrl_frame.grid_columnconfigure(0, weight=1)
        sel_ctrl_frame.grid_columnconfigure(1, weight=1)

        btn_check_all = ctk.CTkButton(sel_ctrl_frame, text="Marcar Filtrados", height=24, fg_color="#34495e", hover_color="#2c3e50", font=ctk.CTkFont(size=11), command=lambda: select_filtered(True))
        btn_check_all.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        btn_uncheck_all = ctk.CTkButton(sel_ctrl_frame, text="Desmarcar Filtrados", height=24, fg_color="#34495e", hover_color="#2c3e50", font=ctk.CTkFont(size=11), command=lambda: select_filtered(False))
        btn_uncheck_all.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Footer Frame
        footer = ctk.CTkFrame(popup, fg_color="transparent")
        footer.grid(row=6, column=0, padx=20, pady=(10, 15), sticky="ew")
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
                
                # Rescan and rebuild UI
                scan_directory()

        delete_btn = ctk.CTkButton(footer, text="Excluir Selecionados", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", height=38, command=on_delete_clicked)
        delete_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        close_btn = ctk.CTkButton(footer, text="Fechar", height=38, fg_color="transparent", border_width=1, command=popup.destroy)
        close_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Initial Scan
        scan_directory()

    def setup_tab_linx_notes(self):
        tab = self.frame_linx_notes
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=0)

        # Header Frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Observações e Anotações (Linx DMS / Apollo)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header_frame, text="Campo de texto livre para anotações do sistema Linx DMS. Salvo automaticamente nas configurações.", font=ctk.CTkFont(size=12, slant="italic")).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Multiline Textbox
        self.linx_notes_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=13), wrap="word")
        self.linx_notes_box.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        # Load initial value from config
        initial_notes = self.app_config.get("linx_notes", "")
        if initial_notes:
            self.linx_notes_box.insert("0.0", initial_notes)

        # Footer Frame (Save Button & Feedback Status)
        footer_frame = ctk.CTkFrame(tab, fg_color="transparent")
        footer_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        self.linx_notes_status_lbl = ctk.CTkLabel(footer_frame, text="", font=ctk.CTkFont(size=12))
        self.linx_notes_status_lbl.grid(row=0, column=0, sticky="w")

        btn_save = ctk.CTkButton(
            footer_frame,
            text="💾 Salvar Observações",
            width=160,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_linx_notes
        )
        btn_save.grid(row=0, column=1, sticky="e")

    def save_linx_notes(self):
        if hasattr(self, "linx_notes_box"):
            notes_text = self.linx_notes_box.get("0.0", "end-1c")
            self.app_config["linx_notes"] = notes_text
            if config.save_config(self.app_config):
                if hasattr(self, "linx_notes_status_lbl"):
                    now_str = datetime.now().strftime("%H:%M:%S")
                    self.linx_notes_status_lbl.configure(text=f"✓ Observações salvas às {now_str}", text_color="#2fa572")



