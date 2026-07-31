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
from ui_nbs import NBSMixin
from ui_apollo import ApolloMixin
from ui_common import CommonMixin

# Set application appearance and theme
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Ajuste global para corrigir a cor do texto no modo claro (evitando texto branco/claro em fundo claro)
ctk.ThemeManager.theme["CTkButton"]["text_color"] = ["#000000", "#FFFFFF"]
if "CTkOptionMenu" in ctk.ThemeManager.theme:
    ctk.ThemeManager.theme["CTkOptionMenu"]["text_color"] = ["#000000", "#FFFFFF"]
if "CTkSegmentedButton" in ctk.ThemeManager.theme:
    ctk.ThemeManager.theme["CTkSegmentedButton"]["text_color"] = ["#000000", "#FFFFFF"]


class AtualizadorApp(ctk.CTk, NBSMixin, ApolloMixin, CommonMixin):
    def __init__(self):
        super().__init__()

        # Load configurations
        self.app_config = config.load_config()
        self.os_type = platform.system()

        # Apply saved appearance mode
        ctk.set_appearance_mode(self.app_config.get("appearance_mode", "Dark"))

        # Window properties
        self.title("Atualizador Sistemas")
        self.geometry("1020x700")
        self.minsize(950, 640)

        # Track UI variables
        self.ftp_password_visible = False
        self.db_credentials_visible = False
        self.brands_list = []
        self.brand_checkboxes = {}  # {brand_name: CTkCheckBox}
        self.brand_widgets_in_grid = []
        self.latest_downloaded_script = ""
        self.download_paused = False
        self.download_cancelled = False
        self.current_downloading_file = None

        # Track Linx UI variables
        self.linx_download_paused = False
        self.linx_download_cancelled = False
        self.linx_current_downloading_file = None
        self.linx_updating = False
        self.linx_update_cancelled = False
        self.mock_service_states = {
            "DFeServico": "ONLINE",
            "RedirecionaDatasnap": "OFFLINE",
            "VerificaServer3Camadas": "OFFLINE"
        }

        # ----------------- SYSTEM SELECTION SCREEN -----------------
        self.frame_system_selection = ctk.CTkFrame(self, fg_color="transparent")

        # Layout Setup (Sidebar + Content Area) - They will be gridded dynamically
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)

        # ----------------- SIDEBAR -----------------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid_rowconfigure(9, weight=1)  # Spacer row (pushed down)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="NBS Atualizador", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.os_label = ctk.CTkLabel(self.sidebar_frame, text=f"S.O.: {self.os_type}", font=ctk.CTkFont(size=12, slant="italic"))
        self.os_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Navigation Buttons (Tabs on the left)
        self.nav_btn1 = ctk.CTkButton(self.sidebar_frame, text="Download & Backup", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("download"))
        self.nav_btn2 = ctk.CTkButton(self.sidebar_frame, text="Executar Scripts", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("execution"))
        self.nav_btn3 = ctk.CTkButton(self.sidebar_frame, text="Cópia para outros servidores", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("distribution"))
        self.nav_btn6 = ctk.CTkButton(self.sidebar_frame, text="Utilitários", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("utilities"))
        self.nav_btn7 = ctk.CTkButton(self.sidebar_frame, text="Atualização CRMWeb", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("crmweb"))
        self.nav_btn4 = ctk.CTkButton(self.sidebar_frame, text="Configurações", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("settings"))
        self.nav_btn5 = ctk.CTkButton(self.sidebar_frame, text="Sobre o App", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("about"))
        self.nav_btn_notes = ctk.CTkButton(self.sidebar_frame, text="📝 Observações", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("nbs_notes"))

        # Linx Navigation Buttons
        self.linx_nav_btn_download = ctk.CTkButton(self.sidebar_frame, text="Download Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_download"))
        self.linx_nav_btn_update = ctk.CTkButton(self.sidebar_frame, text="Atualização Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_update"))
        self.linx_nav_btn_utilities = ctk.CTkButton(self.sidebar_frame, text="Utilitários Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_utilities"))
        self.linx_nav_btn_settings = ctk.CTkButton(self.sidebar_frame, text="Configurações Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_settings"))
        self.linx_nav_btn_about = ctk.CTkButton(self.sidebar_frame, text="Sobre o Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_about"))
        self.linx_nav_btn_notes = ctk.CTkButton(self.sidebar_frame, text="📝 Observações", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_notes"))

        # General back button
        self.nav_btn_back_to_selection = ctk.CTkButton(self.sidebar_frame, text="⬅ Alterar Sistema", anchor="center", height=35, fg_color="transparent", border_width=1, border_color=("#3a7ebf", "#1f538d"), font=ctk.CTkFont(size=12, weight="bold"), command=self.show_system_selection_screen)

        # ----------------- CONTENT CONTAINER -----------------
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Navigation Frames
        self.frame_download = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_execution = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_distribution = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_utilities = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_crmweb = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_about = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_nbs_notes = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        # Linx Navigation Frames
        self.frame_linx_download = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_update = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_utilities = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_settings = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_about = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_notes = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        self.setup_tab_download()
        self.setup_tab_execution()
        self.setup_tab_distribution()
        self.setup_tab_utilities()
        self.setup_tab_crmweb()
        self.setup_tab_settings()
        self.setup_tab_about()
        self.setup_tab_nbs_notes()

        # Set up Linx tabs
        self.setup_tab_linx_download()
        self.setup_tab_linx_update()
        self.setup_tab_linx_utilities()
        self.setup_tab_linx_settings()
        self.setup_tab_linx_about()
        self.setup_tab_linx_notes()

        # Initialize configurations in GUI fields
        self.load_config_into_ui()

        # Trigger auto-detection of last update date
        self.auto_detect_cutoff_date()

        # If brand download checkbox starts checked, fetch them
        if self.download_interfaces_var.get():
            self.fetch_brands()

        # Set up and show selection screen
        self.setup_system_selection_ui()
        self.show_system_selection_screen()

        # Handle window close to auto-save configs
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ----------------- TAB 1: DOWNLOAD & BACKUP -----------------

    def on_closing(self):
        try:
            self.save_ui_to_config()
        except Exception:
            pass
        try:
            self.save_nbs_notes()
        except Exception:
            pass
        try:
            self.save_linx_notes()
        except Exception:
            pass
        self.destroy()


    def auto_detect_cutoff_date(self):
        """Scans the active directory and pre-populates the last update date."""
        c = self.app_config
        path = c.get("atualizacao_path_win", "C:\\Atualizacao") if self.os_type == "Windows" else c.get("atualizacao_path_linux", "./Atualizacao")
        
        self.cutoff_date_entry.delete(0, "end")
        
        last_dt = utils.get_last_update_date(path)
        if last_dt:
            date_str = last_dt.strftime("%d/%m/%Y")
            self.cutoff_date_entry.insert(0, date_str)
            self.log_to_dl_console(f"Última data de atualização detectada a partir de {path}: {date_str}")
        else:
            # Fallback to MinValue or blank, meaning download everything
            self.cutoff_date_entry.insert(0, "")
            self.log_to_dl_console(f"Nenhuma pasta anterior ddMMyyyy encontrada em {path}. Todos os arquivos serão baixados.")

    # ----------------- GENERAL WIDGET UTILS -----------------

    def set_navigation_state(self, state):
        """Habilita ou desabilita os botões da barra lateral de navegação."""
        self.nav_btn1.configure(state=state)
        self.nav_btn2.configure(state=state)
        self.nav_btn3.configure(state=state)
        self.nav_btn4.configure(state=state)
        self.nav_btn5.configure(state=state)
        self.nav_btn6.configure(state=state)
        self.nav_btn7.configure(state=state)
        self.nav_btn_notes.configure(state=state)
        self.linx_nav_btn_download.configure(state=state)
        self.linx_nav_btn_update.configure(state=state)
        self.linx_nav_btn_utilities.configure(state=state)
        self.linx_nav_btn_settings.configure(state=state)
        self.linx_nav_btn_about.configure(state=state)
        self.linx_nav_btn_notes.configure(state=state)


    def show_running_buttons(self):
        """Exibe os botões de pausar e cancelar na interface, ocultando o botão de iniciar."""
        self.start_dl_btn.grid_forget()
        self.pause_dl_btn.grid(row=1, column=1, padx=10, pady=(5, 2), sticky="ew")
        self.cancel_dl_btn.grid(row=2, column=1, padx=10, pady=(2, 5), sticky="ew")
        self.pause_dl_btn.configure(text="Pausar")


    def show_idle_buttons(self):
        """Restaura o botão de iniciar na interface, ocultando os botões de pausar e cancelar."""
        self.pause_dl_btn.grid_forget()
        self.cancel_dl_btn.grid_forget()
        self.start_dl_btn.grid(row=1, column=1, rowspan=2, padx=10, pady=5, sticky="nsew")


    def select_frame(self, name):
        # Reset colors of navigation buttons (active vs inactive)
        self.nav_btn1.configure(fg_color=("#3a7ebf", "#1f538d") if name == "download" else "transparent")
        self.nav_btn2.configure(fg_color=("#3a7ebf", "#1f538d") if name == "execution" else "transparent")
        self.nav_btn3.configure(fg_color=("#3a7ebf", "#1f538d") if name == "distribution" else "transparent")
        self.nav_btn6.configure(fg_color=("#3a7ebf", "#1f538d") if name == "utilities" else "transparent")
        self.nav_btn7.configure(fg_color=("#3a7ebf", "#1f538d") if name == "crmweb" else "transparent")
        self.nav_btn4.configure(fg_color=("#3a7ebf", "#1f538d") if name == "settings" else "transparent")
        self.nav_btn5.configure(fg_color=("#3a7ebf", "#1f538d") if name == "about" else "transparent")
        self.nav_btn_notes.configure(fg_color=("#3a7ebf", "#1f538d") if name == "nbs_notes" else "transparent")

        self.linx_nav_btn_download.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_download" else "transparent")
        self.linx_nav_btn_update.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_update" else "transparent")
        self.linx_nav_btn_utilities.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_utilities" else "transparent")
        self.linx_nav_btn_settings.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_settings" else "transparent")
        self.linx_nav_btn_about.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_about" else "transparent")
        self.linx_nav_btn_notes.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_notes" else "transparent")

        # Hide/show appropriate frame
        if name == "download":
            self.frame_download.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_download.grid_remove()

        if name == "execution":
            self.frame_execution.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_execution.grid_remove()

        if name == "distribution":
            self.frame_distribution.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_distribution.grid_remove()

        if name == "utilities":
            self.frame_utilities.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_utilities.grid_remove()

        if name == "crmweb":
            self.frame_crmweb.grid(row=0, column=0, sticky="nsew")
            self.after(100, self.refresh_crm_service)
        else:
            self.frame_crmweb.grid_remove()

        if name == "settings":
            self.frame_settings.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_settings.grid_remove()

        if name == "about":
            self.frame_about.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_about.grid_remove()

        if name == "nbs_notes":
            self.frame_nbs_notes.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_nbs_notes.grid_remove()

        # Linx frames
        if name == "linx_download":
            self.frame_linx_download.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_linx_download.grid_remove()

        if name == "linx_update":
            self.frame_linx_update.grid(row=0, column=0, sticky="nsew")
            # Auto-refresh services when selecting update frame
            self.after(100, self.refresh_linx_services)
        else:
            self.frame_linx_update.grid_remove()

        if name == "linx_utilities":
            self.frame_linx_utilities.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_linx_utilities.grid_remove()

        if name == "linx_settings":
            self.frame_linx_settings.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_linx_settings.grid_remove()

        if name == "linx_about":
            self.frame_linx_about.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_linx_about.grid_remove()

        if name == "linx_notes":
            self.frame_linx_notes.grid(row=0, column=0, sticky="nsew")
        else:
            self.frame_linx_notes.grid_remove()


    def show_nbs_sidebar(self):
        # Hide all Linx buttons
        self.linx_nav_btn_download.grid_remove()
        self.linx_nav_btn_update.grid_remove()
        self.linx_nav_btn_utilities.grid_remove()
        self.linx_nav_btn_settings.grid_remove()
        self.linx_nav_btn_about.grid_remove()
        self.linx_nav_btn_notes.grid_remove()
        
        # Show all NBS buttons
        self.nav_btn1.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn2.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn3.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn6.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn7.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn4.grid(row=7, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn5.grid(row=8, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn_notes.grid(row=9, column=0, padx=15, pady=5, sticky="ew")
        
        # Show back button
        self.nav_btn_back_to_selection.grid(row=11, column=0, padx=15, pady=15, sticky="ew")


    def show_linx_sidebar(self):
        # Hide all NBS buttons
        self.nav_btn1.grid_remove()
        self.nav_btn2.grid_remove()
        self.nav_btn3.grid_remove()
        self.nav_btn6.grid_remove()
        self.nav_btn7.grid_remove()
        self.nav_btn4.grid_remove()
        self.nav_btn5.grid_remove()
        self.nav_btn_notes.grid_remove()
        
        # Show Linx buttons
        self.linx_nav_btn_download.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_update.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_utilities.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_settings.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_about.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_notes.grid(row=7, column=0, padx=15, pady=5, sticky="ew")
        
        # Show back button
        self.nav_btn_back_to_selection.grid(row=11, column=0, padx=15, pady=15, sticky="ew")


    def setup_system_selection_ui(self):
        # Main container inside frame_system_selection
        self.selection_container = ctk.CTkFrame(self.frame_system_selection, fg_color="transparent")
        self.selection_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title Label
        title_lbl = ctk.CTkLabel(self.selection_container, text="Atualizador de Sistemas", font=ctk.CTkFont(size=26, weight="bold"))
        title_lbl.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        subtitle_lbl = ctk.CTkLabel(self.selection_container, text="Selecione qual sistema você deseja gerenciar:", font=ctk.CTkFont(size=14, slant="italic"))
        subtitle_lbl.grid(row=1, column=0, columnspan=2, pady=(0, 40))
        
        # NBS Card
        self.nbs_card = ctk.CTkFrame(self.selection_container, width=350, height=280, corner_radius=15, border_width=2, border_color="#3a7ebf")
        self.nbs_card.grid(row=2, column=0, padx=20, pady=10)
        self.nbs_card.grid_propagate(False)
        
        # Linx Card
        self.linx_card = ctk.CTkFrame(self.selection_container, width=350, height=280, corner_radius=15, border_width=2, border_color="#2c3e50")
        self.linx_card.grid(row=2, column=1, padx=20, pady=10)
        self.linx_card.grid_propagate(False)
        
        # NBS Card Contents
        nbs_title = ctk.CTkLabel(self.nbs_card, text="Sistema NBS", font=ctk.CTkFont(size=18, weight="bold"))
        nbs_title.pack(pady=(20, 10))
        
        nbs_desc = ctk.CTkLabel(self.nbs_card, text="• Atualização de Módulos (FTP)\n• Execução de Scripts SQL\n• Cópia de Redes (Distribuição)\n• Utilitários & Atualização CRMWeb", justify="left", font=ctk.CTkFont(size=11))
        nbs_desc.pack(anchor="w", padx=45, pady=10)
        
        nbs_btn = ctk.CTkButton(self.nbs_card, text="Atualizar NBS", font=ctk.CTkFont(weight="bold"), height=35, command=lambda: self.enter_system("nbs"))
        nbs_btn.pack(side="bottom", pady=20)
        
        # Linx Card Contents
        linx_title = ctk.CTkLabel(self.linx_card, text="Sistema Linx DMS", font=ctk.CTkFont(size=18, weight="bold"))
        linx_title.pack(pady=(20, 10))
        
        linx_desc = ctk.CTkLabel(self.linx_card, text="• Downloads de Versões (FTP)\n• Pacotes DMS, HPE, Toyota...\n• Suporte a 3 Camadas & Web\n• Atualização Modularizada", justify="left", font=ctk.CTkFont(size=11))
        linx_desc.pack(anchor="w", padx=45, pady=10)
        
        linx_btn = ctk.CTkButton(self.linx_card, text="Atualizar Linx DMS", font=ctk.CTkFont(weight="bold"), height=35, fg_color="#2c3e50", hover_color="#34495e", command=lambda: self.enter_system("linx"))
        linx_btn.pack(side="bottom", pady=20)


    def enter_system(self, system_name):
        self.frame_system_selection.grid_remove()
        
        # Re-grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")
        
        if system_name == "nbs":
            self.title("Atualizador Sistemas - NBS")
            self.logo_label.configure(text="NBS Atualizador")
            self.show_nbs_sidebar()
            self.select_frame("download")
        elif system_name == "linx":
            self.title("Atualizador Sistemas - Linx DMS")
            self.logo_label.configure(text="Linx Atualizador")
            self.show_linx_sidebar()
            self.select_frame("linx_download")


    def show_system_selection_screen(self):
        # Remove sidebar and content from grid
        self.sidebar_frame.grid_remove()
        self.content_frame.grid_remove()
        
        # Reset window grid weights to keep selection centered
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        
        # Show selection screen
        self.title("Atualizador Sistemas - Selecionar Sistema")
        self.frame_system_selection.grid(row=0, column=0, columnspan=2, sticky="nsew")


    def log_to_dl_console(self, message):
        self.console_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.console_log.see("end")


    def log_to_exec_console(self, message):
        self.exec_log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.exec_log_box.see("end")


    def log_to_dist_console(self, message):
        self.dist_console_log.configure(state="normal")
        self.dist_console_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.dist_console_log.see("end")
        self.dist_console_log.configure(state="disabled")

    # ----------------- BRANDS FETCHING AND FILTERING -----------------


if __name__ == "__main__":
    # Ensure Tkinter runs correctly (handles X server issues gracefully on headless servers if needed)
    try:
        app = AtualizadorApp()
        app.mainloop()
    except Exception as e:
        print(f"Erro ao inicializar interface gráfica: {str(e)}")
        sys.exit(1)
