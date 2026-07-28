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

# Set application appearance and theme
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Ajuste global para corrigir a cor do texto no modo claro (evitando texto branco/claro em fundo claro)
ctk.ThemeManager.theme["CTkButton"]["text_color"] = ["#000000", "#FFFFFF"]
if "CTkOptionMenu" in ctk.ThemeManager.theme:
    ctk.ThemeManager.theme["CTkOptionMenu"]["text_color"] = ["#000000", "#FFFFFF"]
if "CTkSegmentedButton" in ctk.ThemeManager.theme:
    ctk.ThemeManager.theme["CTkSegmentedButton"]["text_color"] = ["#000000", "#FFFFFF"]

class AtualizadorApp(ctk.CTk):
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

        # Linx Navigation Buttons
        self.linx_nav_btn_download = ctk.CTkButton(self.sidebar_frame, text="Download Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_download"))
        self.linx_nav_btn_update = ctk.CTkButton(self.sidebar_frame, text="Atualização Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_update"))
        self.linx_nav_btn_utilities = ctk.CTkButton(self.sidebar_frame, text="Utilitários Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_utilities"))
        self.linx_nav_btn_settings = ctk.CTkButton(self.sidebar_frame, text="Configurações Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_settings"))
        self.linx_nav_btn_about = ctk.CTkButton(self.sidebar_frame, text="Sobre o Linx", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.select_frame("linx_about"))

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

        # Linx Navigation Frames
        self.frame_linx_download = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_update = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_utilities = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_settings = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.frame_linx_about = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        self.setup_tab_download()
        self.setup_tab_execution()
        self.setup_tab_distribution()
        self.setup_tab_utilities()
        self.setup_tab_crmweb()
        self.setup_tab_settings()
        self.setup_tab_about()

        # Set up Linx tabs
        self.setup_tab_linx_download()
        self.setup_tab_linx_update()
        self.setup_tab_linx_utilities()
        self.setup_tab_linx_settings()
        self.setup_tab_linx_about()

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
    def setup_tab_download(self):
        tab = self.frame_download
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        # Left Column Frame (Execution Details)
        self.dl_left_frame = ctk.CTkScrollableFrame(tab)
        self.dl_left_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.dl_left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.dl_left_frame, text="Parâmetros de Execução", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Cut-off Date
        ctk.CTkLabel(self.dl_left_frame, text="Data de Corte (Última Atualização):", anchor="w").grid(row=1, column=0, padx=15, pady=(10, 0), sticky="w")
        date_frame = ctk.CTkFrame(self.dl_left_frame, fg_color="transparent")
        date_frame.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        date_frame.grid_columnconfigure(0, weight=1)
        self.cutoff_date_entry = ctk.CTkEntry(date_frame, placeholder_text="DD/MM/AAAA")
        self.cutoff_date_entry.grid(row=0, column=0, sticky="ew")
        self.recalc_btn = ctk.CTkButton(date_frame, text="Recalcular", width=80, command=self.auto_detect_cutoff_date)
        self.recalc_btn.grid(row=0, column=1, padx=(5, 0))

        # Path info recap (read-only visual confirmation)
        paths_frame = ctk.CTkFrame(self.dl_left_frame)
        paths_frame.grid(row=3, column=0, padx=15, pady=20, sticky="ew")
        paths_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(paths_frame, text="Caminhos Ativos de Gravação", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.recap_atualiza_lbl = ctk.CTkLabel(paths_frame, text="Atualização: -", anchor="w", justify="left")
        self.recap_atualiza_lbl.grid(row=1, column=0, padx=10, pady=2, sticky="w")

        self.recap_nbs_lbl = ctk.CTkLabel(paths_frame, text="NBS Local: -", anchor="w", justify="left")
        self.recap_nbs_lbl.grid(row=2, column=0, padx=10, pady=2, sticky="w")

        self.recap_ftp_lbl = ctk.CTkLabel(paths_frame, text="Servidor FTP: -", anchor="w", justify="left")
        self.recap_ftp_lbl.grid(row=3, column=0, padx=10, pady=2, sticky="w")

        # Right Column Frame (Options and Brand Checklist)
        self.dl_right_frame = ctk.CTkScrollableFrame(tab)
        self.dl_right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.dl_right_frame.grid_columnconfigure(0, weight=1)
        self.dl_right_frame.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(self.dl_right_frame, text="Opções de Download", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        # Checkbox Year Transition
        self.transition_year_var = ctk.BooleanVar()
        self.transition_year_check = ctk.CTkCheckBox(self.dl_right_frame, text="Baixar script transição ano:", variable=self.transition_year_var, command=self.toggle_transition_year_field)
        self.transition_year_check.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        
        self.transition_year_entry = ctk.CTkEntry(self.dl_right_frame, placeholder_text="Ano (ex: 2025)", width=120)
        self.transition_year_entry.grid(row=2, column=0, padx=(35, 15), pady=(0, 10), sticky="w")

        # Checkbox NFE
        self.download_nfe_var = ctk.BooleanVar()
        self.download_nfe_check = ctk.CTkCheckBox(self.dl_right_frame, text="Baixar instalador NFE", variable=self.download_nfe_var)
        self.download_nfe_check.grid(row=3, column=0, padx=15, pady=5, sticky="w")

        # Checkbox Brands
        self.download_interfaces_var = ctk.BooleanVar()
        self.download_interfaces_check = ctk.CTkCheckBox(self.dl_right_frame, text="Baixar interfaces de marcas", variable=self.download_interfaces_var, command=self.on_toggle_download_interfaces)
        self.download_interfaces_check.grid(row=4, column=0, padx=15, pady=5, sticky="w")

        # Checkbox Instalação Inicial
        self.initial_installation_var = ctk.BooleanVar()
        self.initial_installation_check = ctk.CTkCheckBox(self.dl_right_frame, text="Instalação Inicial (Ignora data e baixa DLLs)", variable=self.initial_installation_var, command=self.on_toggle_initial_installation)
        self.initial_installation_check.grid(row=5, column=0, padx=15, pady=5, sticky="w")

        # Checkbox Compactar Backup
        self.compress_backup_var = ctk.BooleanVar()
        self.compress_backup_check = ctk.CTkCheckBox(self.dl_right_frame, text="Compactar pasta de backup (.zip)", variable=self.compress_backup_var, command=self.save_ui_to_config)
        self.compress_backup_check.grid(row=6, column=0, padx=15, pady=5, sticky="w")

        # Checkbox Deletar Pasta Original
        self.delete_backup_after_compress_var = ctk.BooleanVar()
        self.delete_backup_after_compress_check = ctk.CTkCheckBox(self.dl_right_frame, text="Excluir pasta de backup após compactar", variable=self.delete_backup_after_compress_var, command=self.save_ui_to_config)
        self.delete_backup_after_compress_check.grid(row=7, column=0, padx=15, pady=5, sticky="w")

        # Scrollable Brand selector
        self.brands_outer_frame = ctk.CTkFrame(self.dl_right_frame, fg_color="transparent")
        self.brands_outer_frame.grid(row=8, column=0, padx=15, pady=5, sticky="nsew")
        self.brands_outer_frame.grid_columnconfigure(0, weight=1)
        self.brands_outer_frame.grid_rowconfigure(2, weight=1)

        self.brands_search_entry = ctk.CTkEntry(self.brands_outer_frame, placeholder_text="Pesquisar marcas...")
        self.brands_search_entry.grid(row=0, column=0, pady=2, sticky="ew")
        self.brands_search_entry.bind("<KeyRelease>", self.filter_brands_list)

        self.brands_loading_label = ctk.CTkLabel(self.brands_outer_frame, text="Marcar a flag para carregar marcas do FTP...", font=ctk.CTkFont(slant="italic"))
        self.brands_loading_label.grid(row=1, column=0, pady=10)

        self.brands_scroll_frame = ctk.CTkScrollableFrame(self.brands_outer_frame, label_text="Marcas Disponíveis no FTP")
        self.brands_scroll_frame.grid_columnconfigure(0, weight=1)

        # Bottom Frame (Status, Progress and Launch Button)
        self.dl_bottom_frame = ctk.CTkFrame(tab)
        self.dl_bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        self.dl_bottom_frame.grid_columnconfigure(0, weight=4)
        self.dl_bottom_frame.grid_columnconfigure(1, weight=1)

        # Log & Console
        self.console_log = ctk.CTkTextbox(self.dl_bottom_frame, height=140, font=ctk.CTkFont(family="monospace", size=11))
        self.console_log.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.dl_status_label = ctk.CTkLabel(self.dl_bottom_frame, text="Pronto para iniciar.", anchor="w")
        self.dl_status_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")

        self.dl_progressbar = ctk.CTkProgressBar(self.dl_bottom_frame)
        self.dl_progressbar.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.dl_progressbar.set(0)

        self.start_dl_btn = ctk.CTkButton(self.dl_bottom_frame, text="Iniciar Processo", font=ctk.CTkFont(size=14, weight="bold"), height=35, command=self.start_download_process)
        self.start_dl_btn.grid(row=1, column=1, rowspan=2, padx=10, pady=5, sticky="nsew")

        self.pause_dl_btn = ctk.CTkButton(self.dl_bottom_frame, text="Pausar", font=ctk.CTkFont(size=13, weight="bold"), height=16, command=self.toggle_pause_download)
        self.cancel_dl_btn = ctk.CTkButton(self.dl_bottom_frame, text="Cancelar", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", height=16, command=self.cancel_download)

    # ----------------- TAB 2: EXECUTAR SCRIPTS -----------------
    def setup_tab_execution(self):
        tab = self.frame_execution
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Content frame
        exec_frame = ctk.CTkFrame(tab)
        exec_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        exec_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(exec_frame, text="Executar Script de Banco de Dados", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        ctk.CTkLabel(exec_frame, text="Selecione o arquivo de script NBS Scripts baixado para rodar as atualizações no banco.", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Select file path
        path_frame = ctk.CTkFrame(exec_frame, fg_color="transparent")
        path_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        self.script_path_entry = ctk.CTkEntry(path_frame, placeholder_text="Selecione o arquivo executável (.exe)...")
        self.script_path_entry.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(path_frame, text="Procurar...", width=90, command=self.browse_script_file).grid(row=0, column=1, padx=(10, 0))

        # DB credentials panel
        self.db_panel = ctk.CTkFrame(exec_frame)
        self.db_panel.grid(row=3, column=0, padx=20, pady=15, sticky="ew")
        self.db_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.db_panel, text="Parâmetros de Banco de Dados (config.json)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        db_grid = ctk.CTkFrame(self.db_panel, fg_color="transparent")
        db_grid.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        db_grid.grid_columnconfigure(0, weight=1)
        db_grid.grid_columnconfigure(1, weight=1)
        db_grid.grid_columnconfigure(2, weight=1)
        db_grid.grid_columnconfigure(3, weight=1)

        # Labels for DB user, password, schema, service name (managed dynamically)
        self.db_user_lbl = ctk.CTkLabel(db_grid, text="Usuário: ••••••••", anchor="w")
        self.db_user_lbl.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.db_schema_lbl = ctk.CTkLabel(db_grid, text="Schema/Host: ••••••••", anchor="w")
        self.db_schema_lbl.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.db_name_lbl = ctk.CTkLabel(db_grid, text="Service Name: ••••••••", anchor="w")
        self.db_name_lbl.grid(row=0, column=2, padx=5, pady=2, sticky="w")

        self.db_pass_lbl = ctk.CTkLabel(db_grid, text="Senha: ••••••••", anchor="w")
        self.db_pass_lbl.grid(row=0, column=3, padx=5, pady=2, sticky="w")

        self.db_toggle_btn = ctk.CTkButton(self.db_panel, text="Exibir Credenciais", width=140, command=self.toggle_db_credentials)
        self.db_toggle_btn.grid(row=2, column=0, padx=15, pady=(5, 10), sticky="w")

        # Action Execution Box
        action_frame = ctk.CTkFrame(exec_frame, fg_color="transparent")
        action_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.run_script_btn = ctk.CTkButton(action_frame, text="Executar como Administrador", font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#d35400", hover_color="#e67e22", command=self.start_script_execution)
        self.run_script_btn.grid(row=0, column=0, sticky="ew")

        # Exec Status & Log
        self.exec_status_label = ctk.CTkLabel(exec_frame, text="Status: Pronto.", font=ctk.CTkFont(size=12, weight="bold"))
        self.exec_status_label.grid(row=5, column=0, padx=20, pady=5, sticky="w")

        self.exec_log_box = ctk.CTkTextbox(exec_frame, height=140, font=ctk.CTkFont(family="monospace", size=11))
        self.exec_log_box.grid(row=6, column=0, padx=20, pady=(5, 15), sticky="ew")

    # ----------------- TAB 3: DISTRIBUIÇÃO -----------------
    def setup_tab_distribution(self):
        tab = self.frame_distribution
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        # Left Column: Servers List management
        self.dist_left_frame = ctk.CTkFrame(tab)
        self.dist_left_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.dist_left_frame.grid_columnconfigure(0, weight=1)
        self.dist_left_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self.dist_left_frame, text="Lista de Servidores para Cópia", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self.dist_left_frame, text="Digite o IP ou caminho UNC (ex: \\\\192.168.1.100\\c$\\NBS):", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # Add Server entry
        add_frame = ctk.CTkFrame(self.dist_left_frame, fg_color="transparent")
        add_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        self.server_entry = ctk.CTkEntry(add_frame, placeholder_text="IP ou \\\\IP\\compartilhamento...")
        self.server_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(add_frame, text="Adicionar", width=70, command=self.add_server_to_list).grid(row=0, column=1, padx=(5, 0))

        # List of servers Scrollable
        self.servers_scroll_frame = ctk.CTkScrollableFrame(self.dist_left_frame, label_text="Servidores Cadastrados")
        self.servers_scroll_frame.grid(row=3, column=0, padx=15, pady=10, sticky="nsew")
        self.servers_scroll_frame.grid_columnconfigure(0, weight=1)

        # Right Column: Distribution Actions and Status
        self.dist_right_frame = ctk.CTkFrame(tab)
        self.dist_right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.dist_right_frame.grid_columnconfigure(0, weight=1)
        self.dist_right_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self.dist_right_frame, text="Parâmetros de Cópia", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.copy_local_var = ctk.BooleanVar()
        self.copy_local_check = ctk.CTkCheckBox(self.dist_right_frame, text="Copiar para a máquina local (C:\\NBS)", variable=self.copy_local_var)
        self.copy_local_check.grid(row=1, column=0, padx=15, pady=5, sticky="w")

        self.copy_servers_var = ctk.BooleanVar()
        self.copy_servers_check = ctk.CTkCheckBox(self.dist_right_frame, text="Copiar para os servidores da lista", variable=self.copy_servers_var)
        self.copy_servers_check.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        # Copy progress list (dynamic per server status display)
        self.copy_status_frame = ctk.CTkScrollableFrame(self.dist_right_frame, label_text="Status da Distribuição", height=130)
        self.copy_status_frame.grid(row=3, column=0, padx=15, pady=10, sticky="nsew")
        self.copy_status_frame.grid_columnconfigure(0, weight=2)
        self.copy_status_frame.grid_columnconfigure(1, weight=1)

        # Operations Log console
        ctk.CTkLabel(self.dist_right_frame, text="Log de Operações:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=4, column=0, padx=15, pady=(5, 0), sticky="w")
        self.dist_console_log = ctk.CTkTextbox(self.dist_right_frame, height=130, font=ctk.CTkFont(family="monospace", size=10))
        self.dist_console_log.grid(row=5, column=0, padx=15, pady=(2, 10), sticky="nsew")
        self.dist_console_log.configure(state="disabled")
        self.dist_right_frame.grid_rowconfigure(5, weight=1)

        # Bottom Bar: Distribute Button
        self.dist_bottom_frame = ctk.CTkFrame(tab)
        self.dist_bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.dist_bottom_frame.grid_columnconfigure(0, weight=3)
        self.dist_bottom_frame.grid_columnconfigure(1, weight=1)

        self.dist_log_label = ctk.CTkLabel(self.dist_bottom_frame, text="Pronto para distribuir atualizações.", anchor="w")
        self.dist_log_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.start_dist_btn = ctk.CTkButton(self.dist_bottom_frame, text="Distribuir Atualização", font=ctk.CTkFont(size=14, weight="bold"), height=35, command=self.start_distribution_process)
        self.start_dist_btn.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

    # ----------------- TAB 3.5: UTILITÁRIOS -----------------
    def setup_tab_utilities(self):
        tab = self.frame_utilities
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(tab, text="Utilitários e Manutenção", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkLabel(tab, text="Ferramentas auxiliares para gerenciamento e limpeza do ambiente local.", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Cleanup card
        cleanup_frame = ctk.CTkFrame(tab)
        cleanup_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        cleanup_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cleanup_frame, text="Limpeza de Executáveis da Pasta NBS", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        details_text = (
            "Esta ferramenta busca todos os arquivos executáveis (.exe) dentro da pasta local do NBS configurada.\n"
            "Permite selecionar de forma interativa a pasta, aplicar filtros Glob/Regex e marcar manualmente os arquivos a excluir.\n"
            "Útil para limpar executáveis temporários ou antigos e economizar espaço."
        )
        ctk.CTkLabel(cleanup_frame, text=details_text, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.cleanup_btn = ctk.CTkButton(cleanup_frame, text="Limpar Executáveis NBS", font=ctk.CTkFont(size=13, weight="bold"), height=35, command=self.open_nbs_cleanup_popup)
        self.cleanup_btn.grid(row=2, column=0, padx=15, pady=(0, 20), sticky="w")

        # Extension cleanup card
        ext_frame = ctk.CTkFrame(tab)
        ext_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        ext_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ext_frame, text="Limpeza de Arquivos por Extensão (NBS)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        ext_details = (
            "Esta ferramenta permite pesquisar e excluir arquivos de qualquer extensão específica (ex: .log, .tmp, .zip)\n"
            "dentro das pastas do NBS ou outro diretório que você escolher.\n"
            "Você define a extensão a ser buscada, filtra os resultados e seleciona manualmente quais remover."
        )
        ctk.CTkLabel(ext_frame, text=ext_details, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.ext_cleanup_btn = ctk.CTkButton(ext_frame, text="Limpar por Extensão NBS", font=ctk.CTkFont(size=13, weight="bold"), height=35, command=lambda: self.open_extension_cleanup_popup("nbs"))
        self.ext_cleanup_btn.grid(row=2, column=0, padx=15, pady=(0, 20), sticky="w")

    def setup_tab_crmweb(self):
        tab = self.frame_crmweb
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Title
        ctk.CTkLabel(tab, text="Atualização CRMWeb", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkLabel(tab, text="Executar utilitários de atualização do CRMWeb com privilégios de Administrador.", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Container cards
        cards_frame = ctk.CTkFrame(tab, fg_color="transparent")
        cards_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)
        cards_frame.grid_columnconfigure(2, weight=1)
        cards_frame.grid_rowconfigure(0, weight=1)

        # Card 1: WEUpdate
        self.crm_card1 = ctk.CTkFrame(cards_frame)
        self.crm_card1.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="nsew")
        self.crm_card1.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.crm_card1, text="WEUpdate (CRMGold)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        ctk.CTkLabel(self.crm_card1, text="Caminho do Executável:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")
        self.crm_path1_entry = ctk.CTkEntry(self.crm_card1)
        self.crm_path1_entry.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        self.crm_path1_entry.insert(0, r"C:\java\Update_BSC_CRMGold\WEUpdate.exe")
        
        ctk.CTkLabel(self.crm_card1, text="Parâmetros de Linha de Comando:", font=ctk.CTkFont(size=11)).grid(row=3, column=0, padx=15, pady=(5, 0), sticky="w")
        self.crm_params1_entry = ctk.CTkEntry(self.crm_card1)
        self.crm_params1_entry.grid(row=4, column=0, padx=15, pady=2, sticky="ew")
        self.crm_params1_entry.insert(0, "-suporte")

        self.crm_btn1 = ctk.CTkButton(self.crm_card1, text="Executar WEUpdate", font=ctk.CTkFont(weight="bold"), height=35, command=self.run_weupdate)
        self.crm_btn1.grid(row=5, column=0, padx=15, pady=20, sticky="ew")

        # Card 2: JManagerClient
        self.crm_card2 = ctk.CTkFrame(cards_frame)
        self.crm_card2.grid(row=0, column=1, padx=5, pady=0, sticky="nsew")
        self.crm_card2.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.crm_card2, text="JManagerClient (Client)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.crm_card2, text="Caminho do Executável:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")
        self.crm_path2_entry = ctk.CTkEntry(self.crm_card2)
        self.crm_path2_entry.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        self.crm_path2_entry.insert(0, r"C:\java\JManagerClient\JManagerClient.exe")

        ctk.CTkLabel(self.crm_card2, text="Parâmetros de Linha de Comando:", font=ctk.CTkFont(size=11)).grid(row=3, column=0, padx=15, pady=(5, 0), sticky="w")
        self.crm_params2_entry = ctk.CTkEntry(self.crm_card2)
        self.crm_params2_entry.grid(row=4, column=0, padx=15, pady=2, sticky="ew")
        self.crm_params2_entry.insert(0, "-suporte -disablehash")

        self.crm_btn2 = ctk.CTkButton(self.crm_card2, text="Executar JManagerClient", font=ctk.CTkFont(weight="bold"), height=35, command=self.run_jmanager)
        self.crm_btn2.grid(row=5, column=0, padx=15, pady=20, sticky="ew")

        # Card 3: Payara Service Monitor
        self.crm_card3 = ctk.CTkFrame(cards_frame)
        self.crm_card3.grid(row=0, column=2, padx=(5, 0), pady=0, sticky="nsew")
        self.crm_card3.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.crm_card3, text="Serviço Payara (CRMWeb)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.crm_card3, text="Nome do Serviço do Windows:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")
        self.crm_service_name_entry = ctk.CTkEntry(self.crm_card3)
        self.crm_service_name_entry.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        self.crm_service_name_entry.insert(0, "domain1")
        self.crm_service_name_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.crm_service_name_entry.bind("<Return>", lambda e: self.save_ui_to_config())

        # Status Display Frame
        status_sub_frame = ctk.CTkFrame(self.crm_card3, fg_color="transparent")
        status_sub_frame.grid(row=3, column=0, padx=15, pady=10, sticky="ew")
        status_sub_frame.grid_columnconfigure(0, weight=1)
        status_sub_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(status_sub_frame, text="Status atual:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w")
        self.crm_service_status_lbl = ctk.CTkLabel(status_sub_frame, text="CONSULTANDO...", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#7f8c8d", text_color="white", corner_radius=6, height=24)
        self.crm_service_status_lbl.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=2)

        self.crm_service_action_btn = ctk.CTkButton(status_sub_frame, text="...", width=70, font=ctk.CTkFont(size=11, weight="bold"), height=24)
        self.crm_service_action_btn.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)

        self.crm_service_refresh_btn = ctk.CTkButton(self.crm_card3, text="Atualizar Status", font=ctk.CTkFont(weight="bold"), command=self.refresh_crm_service)
        self.crm_service_refresh_btn.grid(row=4, column=0, padx=15, pady=(10, 20), sticky="ew")

        # Status & Log Console Frame (Bottom)
        self.crm_bottom_frame = ctk.CTkFrame(tab)
        self.crm_bottom_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.crm_bottom_frame.grid_columnconfigure(0, weight=1)

        self.crm_status_label = ctk.CTkLabel(self.crm_bottom_frame, text="Status: Pronto.", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.crm_status_label.grid(row=0, column=0, padx=15, pady=5, sticky="w")

        self.crm_log_box = ctk.CTkTextbox(self.crm_bottom_frame, height=140, font=ctk.CTkFont(family="monospace", size=11))
        self.crm_log_box.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")

    def run_weupdate(self):
        self._execute_crm_app(self.crm_path1_entry, self.crm_params1_entry, self.crm_btn1, "WEUpdate")

    def run_jmanager(self):
        self._execute_crm_app(self.crm_path2_entry, self.crm_params2_entry, self.crm_btn2, "JManagerClient")

    def _execute_crm_app(self, path_entry, params_entry, btn_widget, app_name):
        path = path_entry.get().strip()
        params = params_entry.get().strip()
        if not path:
            messagebox.showerror("Erro", f"Selecione ou digite o caminho de {app_name}.")
            return
            
        btn_widget.configure(state="disabled")
        self.crm_status_label.configure(text=f"Status: Executando {app_name}...")
        self.crm_log_box.delete("1.0", "end")
        
        threading.Thread(target=self._crm_execution_thread, args=(path, params, btn_widget, app_name), daemon=True).start()

    def _crm_execution_thread(self, path, params, btn_widget, app_name):
        def log(msg):
            self.after(0, lambda: [self.crm_log_box.insert("end", f"{msg}\n"), self.crm_log_box.see("end")])
            
        def status(text):
            self.after(0, lambda: self.crm_status_label.configure(text=f"Status: {text}"))

        if self.os_type != "Windows":
            status(f"Executando {app_name} (Simulação)...")
            log(f"[Linux SIMULADO] Preparando para executar: {path} {params}".strip())
            log("[Linux SIMULADO] Solicitando permissão de Administrador (sudo/runas)...")
            log(f"[Linux SIMULADO] Executando: {path} {params}".strip())
            time.sleep(2)
            log(f"[Linux SIMULADO] Execução simulada finalizada com sucesso.")
            status("Concluído.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", f"{app_name} (Simulado) finalizado com sucesso!"))
            self.after(0, lambda: btn_widget.configure(state="normal"))
            return

        status(f"Iniciando {app_name}...")
        log(f"Iniciando executável elevado: {path} {params}".strip())
        
        # Check if file exists first
        if not os.path.exists(path):
            status("Erro: Não encontrado.")
            log(f"Erro: O executável não existe no caminho especificado: {path}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Executável não encontrado em: {path}"))
            self.after(0, lambda: btn_widget.configure(state="normal"))
            return

        success = utils.execute_script_as_admin(path, log, parameters=params)
        if success:
            status("Concluído.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", f"{app_name} executado e finalizado com sucesso!"))
        else:
            status("Erro ou Cancelado.")
            self.after(0, lambda: messagebox.showerror("Falha", f"Ocorreu um erro ao executar {app_name} ou a elevação UAC foi negada."))
            
        self.after(0, lambda: btn_widget.configure(state="normal"))

    def refresh_crm_service(self):
        """Launches a background thread to check the status of the Payara service."""
        s_name = self.app_config.get("crm_service_payara", "domain1")
        self.crm_service_status_lbl.configure(text="CONSULTANDO...", fg_color="#7f8c8d")
        self.crm_service_action_btn.configure(state="disabled", text="...")
        self.crm_service_refresh_btn.configure(state="disabled", text="Consultando...")
        
        threading.Thread(target=self._refresh_crm_service_thread, args=(s_name,), daemon=True).start()

    def _refresh_crm_service_thread(self, s_name):
        status_val = self.query_service_status(s_name)
        self.after(0, lambda: self.on_crm_service_refreshed(status_val))

    def on_crm_service_refreshed(self, status_val):
        self.crm_service_refresh_btn.configure(state="normal", text="Atualizar Status")
        
        if status_val == "ONLINE":
            self.crm_service_status_lbl.configure(text="ONLINE", fg_color="#27ae60")
            self.crm_service_action_btn.configure(
                state="normal", text="Parar", fg_color="#c0392b", hover_color="#e74c3c",
                command=lambda: self.trigger_crm_service_toggle("stop")
            )
        elif status_val == "OFFLINE":
            self.crm_service_status_lbl.configure(text="OFFLINE", fg_color="#c0392b")
            self.crm_service_action_btn.configure(
                state="normal", text="Iniciar", fg_color="#27ae60", hover_color="#2ecc71",
                command=lambda: self.trigger_crm_service_toggle("start")
            )
        elif status_val == "INDISPONIVEL":
            self.crm_service_status_lbl.configure(text="APENAS WINDOWS", fg_color="#7f8c8d")
            self.crm_service_action_btn.configure(state="disabled", text="Indisponível")
        else:
            self.crm_service_status_lbl.configure(text="INEXISTENTE", fg_color="#7f8c8d")
            self.crm_service_action_btn.configure(state="disabled", text="-")

    def trigger_crm_service_toggle(self, action):
        s_name = self.app_config.get("crm_service_payara", "domain1")
        self.crm_service_status_lbl.configure(text="PROCESSANDO...", fg_color="#e67e22")
        self.crm_service_action_btn.configure(state="disabled", text="...")
        
        threading.Thread(target=self._toggle_crm_service_thread, args=(s_name, action), daemon=True).start()

    def _toggle_crm_service_thread(self, s_name, action):
        if platform.system() != "Windows":
            import time
            time.sleep(1.5)
        else:
            import subprocess
            try:
                subprocess.run(
                    ["sc", action, s_name],
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000
                )
                import time
                time.sleep(2.0)
            except Exception:
                pass
        
        status_val = self.query_service_status(s_name)
        self.after(0, lambda: self.on_crm_service_refreshed(status_val))

    def open_nbs_cleanup_popup(self):
        """Abre uma janela pop-up modal para listar, pesquisar por glob/regex, e excluir arquivos exe do NBS."""
        c = self.app_config

        # Create window
        popup = ctk.CTkToplevel(self)
        popup.title("Limpeza de Executáveis - NBS")
        screen_h = self.winfo_screenheight()
        target_h = min(620, max(440, screen_h - 120))
        popup.geometry(f"640x{target_h}")
        popup.minsize(520, 400)
        popup.grab_set()  # Make modal

        # Title labels
        ctk.CTkLabel(popup, text="Utilitário de Limpeza NBS", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Top Control Frame (Directory selection + Path details)
        top_ctrl = ctk.CTkFrame(popup)
        top_ctrl.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        top_ctrl.grid_columnconfigure(0, weight=1)
        top_ctrl.grid_columnconfigure(1, weight=3)
        top_ctrl.grid_columnconfigure(2, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_ctrl, text="Pasta NBS a Limpar:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        custom_path_var = ctk.StringVar(value="")

        # Directory resolution helper
        def get_resolved_path(dir_key):
            if dir_key == "C:\\NBS":
                return c.get("nbs_path_win", "C:\\NBS") if self.os_type == "Windows" else c.get("nbs_path_linux", "./NBS_Local")
            elif dir_key == "Outro Diretório...":
                return custom_path_var.get()
            return ""

        # OptionMenu selection
        dir_var = ctk.StringVar(value="C:\\NBS")
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

        filter_entry = ctk.CTkEntry(filter_entry_frame, placeholder_text="Ex: *NBS*.exe ou ^modulo_.*\\.exe$")
        filter_entry.grid(row=0, column=0, sticky="ew")

        # Selection tracking dictionaries
        all_files_found = []
        file_checkboxes_widgets = []
        checkbox_selections = {} # Stores {filepath: BooleanVar}

        # Scroll frame for items list
        scroll_frame = ctk.CTkScrollableFrame(popup, label_text="Arquivos Executáveis (.exe) Encontrados")
        scroll_frame.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        popup.grid_rowconfigure(4, weight=1)

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

            filtered_files = []
            for f in all_files_found:
                if matches_pattern(f, filter_text):
                    filtered_files.append(f)

            if not filtered_files:
                empty_lbl = ctk.CTkLabel(scroll_frame, text="Nenhum executável corresponde à pesquisa.", font=ctk.CTkFont(slant="italic"))
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

            if os.path.exists(target_path):
                try:
                    for name in os.listdir(target_path):
                        if os.path.isfile(os.path.join(target_path, name)):
                            name_lower = name.lower()
                            if name_lower.endswith(".exe"):
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
        dir_menu = ctk.CTkOptionMenu(top_ctrl, variable=dir_var, values=["C:\\NBS", "Outro Diretório..."], command=lambda v: scan_directory())
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
                
                scan_directory()

        delete_btn = ctk.CTkButton(footer, text="Excluir Selecionados", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#d9534f", hover_color="#c9302c", height=35, command=on_delete_clicked)
        delete_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        close_btn = ctk.CTkButton(footer, text="Fechar", height=35, fg_color="transparent", border_width=1, command=popup.destroy)
        close_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Load files initial list
        scan_directory()

    # ----------------- TAB 4: CONFIGURAÇÕES -----------------
    def setup_tab_settings(self):
        tab = self.frame_settings
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)

        # Scrollable Settings Container
        self.settings_scroll = ctk.CTkScrollableFrame(tab, label_text="Editar Parâmetros do config.json")
        self.settings_scroll.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # --- SECTION 1: FTP CONFIG ---
        ctk.CTkLabel(self.settings_scroll, text="Configurações do FTP", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(self.settings_scroll, text="FTP Módulos Oficiais:", anchor="w").grid(row=1, column=0, padx=10, pady=(5, 0), sticky="w")
        self.ftp_modules_entry = ctk.CTkEntry(self.settings_scroll, placeholder_text="ftp://...")
        self.ftp_modules_entry.grid(row=2, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.settings_scroll, text="FTP Scripts:", anchor="w").grid(row=3, column=0, padx=10, pady=(5, 0), sticky="w")
        self.ftp_scripts_entry = ctk.CTkEntry(self.settings_scroll, placeholder_text="ftp://...")
        self.ftp_scripts_entry.grid(row=4, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.settings_scroll, text="FTP NFE:", anchor="w").grid(row=5, column=0, padx=10, pady=(5, 0), sticky="w")
        self.ftp_nfe_entry = ctk.CTkEntry(self.settings_scroll, placeholder_text="ftp://...")
        self.ftp_nfe_entry.grid(row=6, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.settings_scroll, text="FTP Interfaces de Marcas:", anchor="w").grid(row=7, column=0, padx=10, pady=(5, 0), sticky="w")
        self.ftp_interfaces_entry = ctk.CTkEntry(self.settings_scroll, placeholder_text="ftp://...")
        self.ftp_interfaces_entry.grid(row=8, column=0, padx=10, pady=2, sticky="ew")

        ctk.CTkLabel(self.settings_scroll, text="FTP DLLs:", anchor="w").grid(row=9, column=0, padx=10, pady=(5, 0), sticky="w")
        self.ftp_dll_entry = ctk.CTkEntry(self.settings_scroll, placeholder_text="ftp://...")
        self.ftp_dll_entry.grid(row=10, column=0, padx=10, pady=2, sticky="ew")

        # FTP Auth
        auth_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        auth_frame.grid(row=11, column=0, padx=10, pady=5, sticky="ew")
        auth_frame.grid_columnconfigure(0, weight=1)
        auth_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(auth_frame, text="Usuário FTP:", anchor="w").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.ftp_user_entry = ctk.CTkEntry(auth_frame)
        self.ftp_user_entry.grid(row=1, column=0, padx=2, pady=2, sticky="ew")

        ctk.CTkLabel(auth_frame, text="Senha FTP:", anchor="w").grid(row=0, column=1, padx=2, pady=2, sticky="w")
        pw_sub_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        pw_sub_frame.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        pw_sub_frame.grid_columnconfigure(0, weight=1)
        
        self.ftp_pass_entry = ctk.CTkEntry(pw_sub_frame, show="*")
        self.ftp_pass_entry.grid(row=0, column=0, sticky="ew")
        self.ftp_pass_btn = ctk.CTkButton(pw_sub_frame, text="👁", width=30, command=self.toggle_ftp_password)
        self.ftp_pass_btn.grid(row=0, column=1, padx=(2, 0))

        # --- SECTION 2: PATHS CONFIG ---
        ctk.CTkLabel(self.settings_scroll, text="Caminhos Locais", font=ctk.CTkFont(size=14, weight="bold")).grid(row=12, column=0, padx=10, pady=(15, 5), sticky="w")

        ctk.CTkLabel(self.settings_scroll, text="Pasta C:\\Atualizacao (Local):", anchor="w").grid(row=13, column=0, padx=10, pady=(5, 0), sticky="w")
        path_up_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        path_up_frame.grid(row=14, column=0, padx=10, pady=2, sticky="ew")
        path_up_frame.grid_columnconfigure(0, weight=1)
        self.atualiza_path_entry = ctk.CTkEntry(path_up_frame)
        self.atualiza_path_entry.grid(row=0, column=0, sticky="ew")
        self.atualiza_path_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.atualiza_path_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_up_frame, text="...", width=30, command=lambda: self.browse_directory(self.atualiza_path_entry)).grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(self.settings_scroll, text="Pasta C:\\NBS (Local):", anchor="w").grid(row=15, column=0, padx=10, pady=(5, 0), sticky="w")
        path_nbs_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        path_nbs_frame.grid(row=16, column=0, padx=10, pady=2, sticky="ew")
        path_nbs_frame.grid_columnconfigure(0, weight=1)
        self.nbs_path_entry = ctk.CTkEntry(path_nbs_frame)
        self.nbs_path_entry.grid(row=0, column=0, sticky="ew")
        self.nbs_path_entry.bind("<FocusOut>", lambda e: self.save_ui_to_config())
        self.nbs_path_entry.bind("<Return>", lambda e: self.save_ui_to_config())
        ctk.CTkButton(path_nbs_frame, text="...", width=30, command=lambda: self.browse_directory(self.nbs_path_entry)).grid(row=0, column=1, padx=(5, 0))

        # --- SECTION 3: DB CONFIG ---
        ctk.CTkLabel(self.settings_scroll, text="Banco de Dados", font=ctk.CTkFont(size=14, weight="bold")).grid(row=17, column=0, padx=10, pady=(15, 5), sticky="w")

        db_inputs_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        db_inputs_frame.grid(row=18, column=0, padx=10, pady=5, sticky="ew")
        db_inputs_frame.grid_columnconfigure(0, weight=1)
        db_inputs_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(db_inputs_frame, text="Usuário Banco:", anchor="w").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.db_user_entry = ctk.CTkEntry(db_inputs_frame)
        self.db_user_entry.grid(row=1, column=0, padx=2, pady=2, sticky="ew")

        ctk.CTkLabel(db_inputs_frame, text="Senha Banco:", anchor="w").grid(row=0, column=1, padx=2, pady=2, sticky="w")
        self.db_pass_entry = ctk.CTkEntry(db_inputs_frame, show="*")
        self.db_pass_entry.grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        ctk.CTkLabel(db_inputs_frame, text="Schema/Host Banco:", anchor="w").grid(row=2, column=0, padx=2, pady=2, sticky="w")
        self.db_schema_entry = ctk.CTkEntry(db_inputs_frame)
        self.db_schema_entry.grid(row=3, column=0, padx=2, pady=2, sticky="ew")

        ctk.CTkLabel(db_inputs_frame, text="Service Name Banco:", anchor="w").grid(row=2, column=1, padx=2, pady=2, sticky="w")
        self.db_name_entry = ctk.CTkEntry(db_inputs_frame)
        self.db_name_entry.grid(row=3, column=1, padx=2, pady=2, sticky="ew")

        # --- SECTION 3.5: APPEARANCE CONFIG ---
        ctk.CTkLabel(self.settings_scroll, text="Aparência Visual", font=ctk.CTkFont(size=14, weight="bold")).grid(row=19, column=0, padx=10, pady=(15, 5), sticky="w")
        self.settings_appearance_menu = ctk.CTkOptionMenu(self.settings_scroll, values=["Dark", "Light", "System"])
        self.settings_appearance_menu.grid(row=20, column=0, padx=10, pady=5, sticky="w")

        # --- SECTION 4: SAVE BUTTON FRAME ---
        save_frame = ctk.CTkFrame(tab, fg_color="transparent")
        save_frame.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        save_frame.grid_columnconfigure(0, weight=1)

        self.save_settings_btn = ctk.CTkButton(save_frame, text="Salvar Configurações", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.save_settings_manually)
        self.save_settings_btn.grid(row=0, column=0, sticky="ew")

    # ----------------- CONFIG & INITIALIZATION UTILS -----------------
    def load_config_into_ui(self):
        """Pre-populates GUI fields with values loaded from config.json."""
        self.loading_config = True
        c = self.app_config

        # Helper to safely clear and write to entry
        def set_entry_text(entry, text):
            entry.delete(0, "end")
            entry.insert(0, text)

        # FTP URLs
        set_entry_text(self.ftp_modules_entry, c.get("ftp_modules_url", ""))
        set_entry_text(self.ftp_scripts_entry, c.get("ftp_scripts_url", ""))
        set_entry_text(self.ftp_nfe_entry, c.get("ftp_nfe_url", ""))
        set_entry_text(self.ftp_interfaces_entry, c.get("ftp_interfaces_url", ""))
        set_entry_text(self.ftp_dll_entry, c.get("ftp_dll_url", ""))

        # FTP Auth
        set_entry_text(self.ftp_user_entry, c.get("ftp_user", ""))
        set_entry_text(self.ftp_pass_entry, c.get("ftp_password", ""))

        # Local Paths (based on OS)
        if self.os_type == "Windows":
            set_entry_text(self.atualiza_path_entry, c.get("atualizacao_path_win", ""))
            set_entry_text(self.nbs_path_entry, c.get("nbs_path_win", ""))
        else:
            set_entry_text(self.atualiza_path_entry, c.get("atualizacao_path_linux", ""))
            set_entry_text(self.nbs_path_entry, c.get("nbs_path_linux", ""))

        # Database Configuration
        set_entry_text(self.db_user_entry, c.get("db_user", ""))
        set_entry_text(self.db_pass_entry, c.get("db_password", ""))
        set_entry_text(self.db_schema_entry, c.get("db_schema", ""))
        set_entry_text(self.db_name_entry, c.get("db_name", ""))

        # CRM service config loading
        set_entry_text(self.crm_service_name_entry, c.get("crm_service_payara", "domain1"))

        # Options
        self.transition_year_var.set(c.get("transition_year_enabled", False))
        set_entry_text(self.transition_year_entry, c.get("transition_year_value", "2025"))
        self.toggle_transition_year_field()

        self.download_nfe_var.set(c.get("download_nfe", False))
        self.download_interfaces_var.set(c.get("download_interfaces", False))
        self.initial_installation_var.set(c.get("initial_installation", False))
        self.compress_backup_var.set(c.get("compress_backup", False))
        self.delete_backup_after_compress_var.set(c.get("delete_backup_after_compress", False))
        self.settings_appearance_menu.set(c.get("appearance_mode", "Dark"))
        if hasattr(self, "linx_settings_appearance_menu"):
            self.linx_settings_appearance_menu.set(c.get("appearance_mode", "Dark"))
        self.on_toggle_initial_installation()

        # Copy variables
        self.copy_local_var.set(c.get("copy_local", True))
        self.copy_servers_var.set(c.get("copy_servers", True))

        # Update visual recap labels on Tab 1
        p_up = c.get("atualizacao_path_win", "") if self.os_type == "Windows" else c.get("atualizacao_path_linux", "")
        p_nbs = c.get("nbs_path_win", "") if self.os_type == "Windows" else c.get("nbs_path_linux", "")
        self.recap_atualiza_lbl.configure(text=f"Atualização: {p_up}")
        self.recap_nbs_lbl.configure(text=f"NBS Local: {p_nbs}")
        
        ftp_url = c.get("ftp_modules_url", "")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(ftp_url)
            self.recap_ftp_lbl.configure(text=f"FTP: {parsed.netloc or ftp_url}")
        except Exception:
            self.recap_ftp_lbl.configure(text=f"FTP: {ftp_url}")

        # Populate servers list
        self.refresh_servers_list_ui()

        # Linx parameters loading
        self.linx_package_menu.set(c.get("linx_package", "LINXDMS"))
        set_entry_text(self.linx_version_entry, c.get("linx_version", "v5.19"))
        if self.os_type == "Windows":
            set_entry_text(self.linx_path_entry, c.get("linx_download_path_win", ""))
        else:
            set_entry_text(self.linx_path_entry, c.get("linx_download_path_linux", ""))

        self.linx_dl_delphi_var.set(c.get("linx_download_delphi", True))
        self.linx_dl_server_var.set(c.get("linx_download_server", False))
        self.linx_dl_client_var.set(c.get("linx_download_client", False))
        self.linx_dl_web_var.set(c.get("linx_download_web", False))
        self.linx_dl_comissoes_var.set(c.get("linx_download_comissoes", False))
        self.linx_dl_apoio_trocafornec_var.set(c.get("linx_download_apoio_trocafornec", False))
        self.linx_dl_apoio_trocaserie_var.set(c.get("linx_download_apoio_trocaserie", False))
        self.linx_dl_apoio_verificadiaria_var.set(c.get("linx_download_apoio_verificadiaria", False))
        self.linx_dl_integrador_var.set(c.get("linx_download_integrador", False))
        self.linx_backup_apollo_var.set(c.get("linx_backup_apollo", False))

        # Linx settings templates
        set_entry_text(self.linx_url_delphi_entry, c.get("linx_url_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_delphi_template"])
        set_entry_text(self.linx_url_server_entry, c.get("linx_url_server_template", "").strip() or config.DEFAULT_CONFIG["linx_url_server_template"])
        set_entry_text(self.linx_url_client_entry, c.get("linx_url_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_client_template"])
        set_entry_text(self.linx_url_web_entry, c.get("linx_url_web_template", "").strip() or config.DEFAULT_CONFIG["linx_url_web_template"])
        set_entry_text(self.linx_url_comissoes_delphi_entry, c.get("linx_url_comissoes_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_delphi_template"])
        set_entry_text(self.linx_url_comissoes_client_entry, c.get("linx_url_comissoes_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_client_template"])
        set_entry_text(self.linx_url_apoio_entry, c.get("linx_url_apoio_template", "").strip() or config.DEFAULT_CONFIG["linx_url_apoio_template"])
        set_entry_text(self.linx_url_integrador_entry, c.get("linx_url_integrador_template", "").strip() or config.DEFAULT_CONFIG["linx_url_integrador_template"])

        # Load Linx services
        set_entry_text(self.linx_service_dfe_entry, c.get("linx_service_dfe", "DFeServico"))
        set_entry_text(self.linx_service_datasnap_entry, c.get("linx_service_datasnap", "RedirecionaDatasnap"))
        set_entry_text(self.linx_service_3camadas_entry, c.get("linx_service_3camadas", "VerificaServer3Camadas"))
        set_entry_text(self.linx_service_integrador_entry, c.get("linx_service_integrador", "dmLDIServer"))
        if hasattr(self, 'linx_kill_pattern_entry'):
            set_entry_text(self.linx_kill_pattern_entry, c.get("linx_kill_process_pattern", "wsContabil"))

        # Load Linx target paths
        if self.os_type == "Windows":
            set_entry_text(self.linx_path_normal_entry, c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza"))
            set_entry_text(self.linx_path_server_entry, c.get("linx_path_server_win", "C:\\3Camadas"))
            set_entry_text(self.linx_path_client_entry, c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza"))
        else:
            set_entry_text(self.linx_path_normal_entry, c.get("linx_path_normal_linux", "./Apollo_Atualiza"))
            set_entry_text(self.linx_path_server_entry, c.get("linx_path_server_linux", "./3Camadas"))
            set_entry_text(self.linx_path_client_entry, c.get("linx_path_client_linux", "./3Camadas_Atualiza"))

        # Update destination labels on Update tab
        p_normal = c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_normal_linux", "./Apollo_Atualiza")
        p_server = c.get("linx_path_server_win", "C:\\3Camadas") if self.os_type == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
        p_client = c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_client_linux", "./3Camadas_Atualiza")
        
        self.dest_normal_lbl.configure(text=f"Apollo/Atualiza: {p_normal}")
        self.dest_server_lbl.configure(text=f"3Camadas Server: {p_server}")
        self.dest_client_lbl.configure(text=f"3Camadas Client: {p_client}")

        self.update_db_credentials_display()
        self.loading_config = False

    def save_ui_to_config(self):
        """Retrieves values from GUI and saves them back to config.json."""
        if getattr(self, "loading_config", False):
            return
        c = self.app_config

        # FTP URLs
        c["ftp_modules_url"] = self.ftp_modules_entry.get()
        c["ftp_scripts_url"] = self.ftp_scripts_entry.get()
        c["ftp_nfe_url"] = self.ftp_nfe_entry.get()
        c["ftp_interfaces_url"] = self.ftp_interfaces_entry.get()
        c["ftp_dll_url"] = self.ftp_dll_entry.get()

        # FTP Auth
        c["ftp_user"] = self.ftp_user_entry.get()
        c["ftp_password"] = self.ftp_pass_entry.get()

        # Paths (based on OS)
        if self.os_type == "Windows":
            c["atualizacao_path_win"] = self.atualiza_path_entry.get()
            c["nbs_path_win"] = self.nbs_path_entry.get()
        else:
            c["atualizacao_path_linux"] = self.atualiza_path_entry.get()
            c["nbs_path_linux"] = self.nbs_path_entry.get()

        # Database Parameters
        c["db_user"] = self.db_user_entry.get()
        c["db_password"] = self.db_pass_entry.get()
        c["db_schema"] = self.db_schema_entry.get()
        c["db_name"] = self.db_name_entry.get()

        # CRM service config saving
        c["crm_service_payara"] = self.crm_service_name_entry.get()

        # Options
        c["transition_year_enabled"] = self.transition_year_var.get()
        c["transition_year_value"] = self.transition_year_entry.get()
        c["download_nfe"] = self.download_nfe_var.get()
        c["download_interfaces"] = self.download_interfaces_var.get()
        c["initial_installation"] = self.initial_installation_var.get()
        c["compress_backup"] = self.compress_backup_var.get()
        c["delete_backup_after_compress"] = self.delete_backup_after_compress_var.get()
        # Synchronize and apply the appearance theme change immediately upon saving
        current_appearance = c.get("appearance_mode", "Dark")
        nbs_appearance = self.settings_appearance_menu.get()
        linx_appearance = self.linx_settings_appearance_menu.get() if hasattr(self, "linx_settings_appearance_menu") else current_appearance

        if nbs_appearance != current_appearance:
            selected_appearance = nbs_appearance
            if hasattr(self, "linx_settings_appearance_menu"):
                self.linx_settings_appearance_menu.set(nbs_appearance)
        elif linx_appearance != current_appearance:
            selected_appearance = linx_appearance
            self.settings_appearance_menu.set(linx_appearance)
        else:
            selected_appearance = nbs_appearance

        c["appearance_mode"] = selected_appearance
        ctk.set_appearance_mode(selected_appearance)

        # Copy variables
        c["copy_local"] = self.copy_local_var.get()
        c["copy_servers"] = self.copy_servers_var.get()

        # Save selected interfaces
        selected_brands = []
        for brand, check_widget in self.brand_checkboxes.items():
            if check_widget.get():
                selected_brands.append(brand)
        c["selected_interfaces"] = selected_brands

        # Linx parameters saving
        c["linx_package"] = self.linx_package_menu.get()
        c["linx_version"] = self.linx_version_entry.get()
        if self.os_type == "Windows":
            c["linx_download_path_win"] = self.linx_path_entry.get()
        else:
            c["linx_download_path_linux"] = self.linx_path_entry.get()

        c["linx_download_delphi"] = self.linx_dl_delphi_var.get()
        c["linx_download_server"] = self.linx_dl_server_var.get()
        c["linx_download_client"] = self.linx_dl_client_var.get()
        c["linx_download_web"] = self.linx_dl_web_var.get()
        c["linx_download_comissoes"] = self.linx_dl_comissoes_var.get()
        c["linx_download_apoio_trocafornec"] = self.linx_dl_apoio_trocafornec_var.get()
        c["linx_download_apoio_trocaserie"] = self.linx_dl_apoio_trocaserie_var.get()
        c["linx_download_apoio_verificadiaria"] = self.linx_dl_apoio_verificadiaria_var.get()
        c["linx_download_integrador"] = self.linx_dl_integrador_var.get()
        c["linx_backup_apollo"] = self.linx_backup_apollo_var.get()

        # Linx settings templates
        c["linx_url_delphi_template"] = self.linx_url_delphi_entry.get()
        c["linx_url_server_template"] = self.linx_url_server_entry.get()
        c["linx_url_client_template"] = self.linx_url_client_entry.get()
        c["linx_url_web_template"] = self.linx_url_web_entry.get()
        c["linx_url_comissoes_delphi_template"] = self.linx_url_comissoes_delphi_entry.get()
        c["linx_url_comissoes_client_template"] = self.linx_url_comissoes_client_entry.get()
        c["linx_url_apoio_template"] = self.linx_url_apoio_entry.get()
        c["linx_url_integrador_template"] = self.linx_url_integrador_entry.get()

        # Linx service names
        c["linx_service_dfe"] = self.linx_service_dfe_entry.get()
        c["linx_service_datasnap"] = self.linx_service_datasnap_entry.get()
        c["linx_service_3camadas"] = self.linx_service_3camadas_entry.get()
        c["linx_service_integrador"] = self.linx_service_integrador_entry.get()
        if hasattr(self, 'linx_kill_pattern_entry'):
            c["linx_kill_process_pattern"] = self.linx_kill_pattern_entry.get().strip()

        # Linx install paths
        if self.os_type == "Windows":
            c["linx_path_normal_win"] = self.linx_path_normal_entry.get()
            c["linx_path_server_win"] = self.linx_path_server_entry.get()
            c["linx_path_client_win"] = self.linx_path_client_entry.get()
        else:
            c["linx_path_normal_linux"] = self.linx_path_normal_entry.get()
            c["linx_path_server_linux"] = self.linx_path_server_entry.get()
            c["linx_path_client_linux"] = self.linx_path_client_entry.get()

        # Save
        config.save_config(c)

    def save_settings_manually(self):
        self.save_ui_to_config()
        self.load_config_into_ui() # Refreshes recap labels
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")

    def on_closing(self):
        try:
            self.save_ui_to_config()
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
    def toggle_ftp_password(self):
        if self.ftp_password_visible:
            self.ftp_pass_entry.configure(show="*")
            self.ftp_pass_btn.configure(text="👁")
            self.ftp_password_visible = False
        else:
            self.ftp_pass_entry.configure(show="")
            self.ftp_pass_btn.configure(text="🔒")
            self.ftp_password_visible = True

    def update_db_credentials_display(self):
        c = self.app_config
        u = c.get("db_user", "Não Configurado")
        s = c.get("db_schema", "Não Configurado")
        n = c.get("db_name", "Não Configurado")
        p = c.get("db_password", "Não Configurado")

        if self.db_credentials_visible:
            self.db_user_lbl.configure(text=f"Usuário: {u}")
            self.db_schema_lbl.configure(text=f"Schema/Host: {s}")
            self.db_name_lbl.configure(text=f"Service Name: {n}")
            self.db_pass_lbl.configure(text=f"Senha: {p}")
            self.db_toggle_btn.configure(text="Ocultar Credenciais")
        else:
            self.db_user_lbl.configure(text=f"Usuário: {len(u) * '•' if u else '••••••••'}")
            self.db_schema_lbl.configure(text=f"Schema/Host: {len(s) * '•' if s else '••••••••'}")
            self.db_name_lbl.configure(text=f"Service Name: {len(n) * '•' if n else '••••••••'}")
            self.db_pass_lbl.configure(text=f"Senha: {len(p) * '•' if p else '••••••••'}")
            self.db_toggle_btn.configure(text="Exibir Credenciais")

    def toggle_db_credentials(self):
        self.db_credentials_visible = not self.db_credentials_visible
        self.update_db_credentials_display()

    def toggle_transition_year_field(self):
        if self.transition_year_var.get():
            self.transition_year_entry.configure(state="normal")
        else:
            self.transition_year_entry.configure(state="disabled")

    def browse_directory(self, entry_widget):
        selected = filedialog.askdirectory()
        if selected:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, os.path.normpath(selected))
            self.save_ui_to_config()

    def browse_script_file(self):
        selected = filedialog.askopenfilename(filetypes=[("Arquivos Executáveis", "*.exe"), ("Todos os Arquivos", "*.*")])
        if selected:
            self.script_path_entry.delete(0, "end")
            self.script_path_entry.insert(0, os.path.normpath(selected))

    def set_navigation_state(self, state):
        """Habilita ou desabilita os botões da barra lateral de navegação."""
        self.nav_btn1.configure(state=state)
        self.nav_btn2.configure(state=state)
        self.nav_btn3.configure(state=state)
        self.nav_btn4.configure(state=state)
        self.nav_btn5.configure(state=state)
        self.nav_btn6.configure(state=state)

    def set_download_inputs_state(self, state):
        """Habilita ou desabilita todos os inputs e controles da aba de download."""
        self.cutoff_date_entry.configure(state=state)
        
        if state == "disabled":
            self.transition_year_entry.configure(state="disabled")
        else:
            self.toggle_transition_year_field()
            
        self.brands_search_entry.configure(state=state)
        self.recalc_btn.configure(state=state)
        
        self.transition_year_check.configure(state=state)
        self.download_nfe_check.configure(state=state)
        self.download_interfaces_check.configure(state=state)
        self.initial_installation_check.configure(state=state)
        self.compress_backup_check.configure(state=state)
        self.delete_backup_after_compress_check.configure(state=state)
        
        for chk in self.brand_checkboxes.values():
            chk.configure(state=state)

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

    def toggle_pause_download(self):
        """Alterna o estado de pausa do processo de download."""
        if self.download_paused:
            self.download_paused = False
            self.pause_dl_btn.configure(text="Pausar")
            self.log_to_dl_console("Processo retomado.")
            self.dl_status_label.configure(text="Retomando download...")
        else:
            self.download_paused = True
            self.pause_dl_btn.configure(text="Retomar")
            self.log_to_dl_console("Processo pausado. Aguardando...")
            self.dl_status_label.configure(text="Pausado.")

    def cancel_download(self):
        """Solicita o cancelamento do processo de download."""
        self.download_cancelled = True
        self.download_paused = False  # Destrava se estiver pausado para que possa finalizar
        self.log_to_dl_console("Solicitação de cancelamento enviada. Aguardando finalização...")
        self.dl_status_label.configure(text="Cancelando...")

    def select_frame(self, name):
        # Reset colors of navigation buttons (active vs inactive)
        self.nav_btn1.configure(fg_color=("#3a7ebf", "#1f538d") if name == "download" else "transparent")
        self.nav_btn2.configure(fg_color=("#3a7ebf", "#1f538d") if name == "execution" else "transparent")
        self.nav_btn3.configure(fg_color=("#3a7ebf", "#1f538d") if name == "distribution" else "transparent")
        self.nav_btn6.configure(fg_color=("#3a7ebf", "#1f538d") if name == "utilities" else "transparent")
        self.nav_btn7.configure(fg_color=("#3a7ebf", "#1f538d") if name == "crmweb" else "transparent")
        self.nav_btn4.configure(fg_color=("#3a7ebf", "#1f538d") if name == "settings" else "transparent")
        self.nav_btn5.configure(fg_color=("#3a7ebf", "#1f538d") if name == "about" else "transparent")

        self.linx_nav_btn_download.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_download" else "transparent")
        self.linx_nav_btn_update.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_update" else "transparent")
        self.linx_nav_btn_utilities.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_utilities" else "transparent")
        self.linx_nav_btn_settings.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_settings" else "transparent")
        self.linx_nav_btn_about.configure(fg_color=("#3a7ebf", "#1f538d") if name == "linx_about" else "transparent")

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

    def show_nbs_sidebar(self):
        # Hide all Linx buttons
        self.linx_nav_btn_download.grid_remove()
        self.linx_nav_btn_update.grid_remove()
        self.linx_nav_btn_utilities.grid_remove()
        self.linx_nav_btn_settings.grid_remove()
        self.linx_nav_btn_about.grid_remove()
        
        # Show all NBS buttons
        self.nav_btn1.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn2.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn3.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn6.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn7.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn4.grid(row=7, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btn5.grid(row=8, column=0, padx=15, pady=5, sticky="ew")
        
        # Show back button
        self.nav_btn_back_to_selection.grid(row=10, column=0, padx=15, pady=15, sticky="ew")

    def show_linx_sidebar(self):
        # Hide all NBS buttons
        self.nav_btn1.grid_remove()
        self.nav_btn2.grid_remove()
        self.nav_btn3.grid_remove()
        self.nav_btn6.grid_remove()
        self.nav_btn7.grid_remove()
        self.nav_btn4.grid_remove()
        self.nav_btn5.grid_remove()
        
        # Show Linx buttons
        self.linx_nav_btn_download.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_update.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_utilities.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_settings.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        self.linx_nav_btn_about.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        
        # Show back button
        self.nav_btn_back_to_selection.grid(row=10, column=0, padx=15, pady=15, sticky="ew")

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

    def setup_tab_about(self):
        tab = self.frame_about
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(tab, text="Sobre o Atualizador NBS", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        # Dev info
        info_frame = ctk.CTkFrame(tab)
        info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_frame, text="Informações do Desenvolvedor e Versão", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        details_text = (
            "Desenvolvedor: Robson Santos\n"
            "Contato: robsonshk@gmail.com\n"
            "Versão do Programa: 1.2.9\n"
            "Finalidade: Facilitar a automação e controle do processo de atualizações de sistemas NBS."
        )
        ctk.CTkLabel(info_frame, text=details_text, justify="left", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        # Changelog Section
        ctk.CTkLabel(tab, text="Histórico de Alterações (Changelog)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")

        self.changelog_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="monospace", size=11))
        self.changelog_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        changelog_text = (
            "=== Versão 1.2.9 ===\n"
            "- Adicionado painel de monitoramento e controle (iniciar/parar) do serviço do Payara (nome padrão 'domain1') na aba de Atualização CRMWeb, permitindo configurar nomes de serviço customizados.\n\n"
            "=== Versão 1.2.8  ===\n"
            "- Adicionado o novo menu 'Atualização CRMWeb' no painel do sistema NBS.\n"
            "- Implementada a execução elevada como administrador (UAC) de utilitários CRMWeb (WEUpdate.exe e JManagerClient.exe) com passagem dinâmica de parâmetros de linha de comando.\n"
            "- Criada interface de cards dedicada com log detalhado e mocks para simulação em ambiente Linux.\n\n"
            "=== Versão 1.2.7  ===\n"
            "- Ajustado o Utilitário de Limpeza da pasta NBS para suportar seleção dinâmica de pastas, buscas por Glob/Regex e controle de filtragem (limitado a arquivos .exe).\n"
            "- Adicionada a nova ferramenta de Limpeza por Extensão na aba NBS para permitir a busca e exclusão segura de tipos de arquivos customizados (.log, .tmp, .zip, etc.).\n\n"
            "=== Versão 1.2.6  ===\n"
            "- Implementada criptografia simétrica (XOR + Base64) nas configurações locais, ocultando credenciais de banco e FTP contra visualização em plain-text.\n"
            "- Redirecionado o armazenamento das configurações para as pastas padrão do usuário (%APPDATA% no Windows e ~/.config no Linux) com o nome 'config.enc'.\n"
            "- Criado fluxo de migração automática e exclusão segura do arquivo 'config.json' legado.\n"
            "- Corrigido flickering/redimensionamento no grid de credenciais de banco de dados na aba de Scripts.\n\n"
            "=== Versão 1.2.5  ===\n"
            "- Corrigida globalmente a cor do texto dos botões, menus de opções e botões segmentados no modo claro.\n"
            "- A correção foi aplicada diretamente no dicionário global de temas (ThemeManager.theme), evitando código hardcoded nos widgets.\n\n"
            "=== Versão 1.2.4  ===\n"
            "- Ativado o callback de log do processo de distribuição de arquivos (Cópia para servidores).\n"
            "- Adicionado um Console de Log (textbox) em tempo real na tela de Distribuição.\n"
            "- Implementada geração automática do arquivo 'distribuicao.log' na pasta de atualização do dia para auditoria de erros e renomeações.\n\n"
            "=== Versão 1.2.3  ===\n"
            "- Adicionada validação do backup local para evitar cópias e compactações desnecessárias caso o backup da pasta local do NBS já exista e esteja atualizado.\n\n"
            "=== Versão 1.2.2  ===\n"
            "- Adicionada validação de arquivos já baixados localmente para pular a transferência de arquivos idênticos.\n"
            "- Implementada comparação por hash MD5 do servidor (se suportado via comandos FTP MD5/XMD5) e fallback por tamanho de arquivo.\n\n"
            "=== Versão 1.2.1  ===\n"
            "- Adicionado travamento de todos os inputs, checkboxes e botão 'Recalcular' da aba de download durante a execução (incluindo em pausa).\n"
            "- Configurado o desbloqueio automático dos inputs da aba de download apenas ao finalizar ou cancelar o processo.\n\n"
            "=== Versão 1.2.0  ===\n"
            "- Corrigido bug NameError 'shutil' is not defined ao deletar a pasta original de backup no Windows/Linux.\n\n"
            "=== Versão 1.1.9  ===\n"
            "- Adicionada nova aba de 'Utilitários' na barra lateral.\n"
            "- Desenvolvida ferramenta de 'Limpeza de Executáveis da Pasta NBS' local.\n"
            "- Implementado pop-up modal para listagem de arquivos (.exe) com seleção por checkbox.\n"
            "- Adicionada caixa de confirmação dupla com listagem dos executáveis marcados antes da exclusão física.\n\n"
            "=== Versão 1.1.8  ===\n"
            "- Movido o controle de Aparência (Tema) da barra lateral para a tela de Configurações.\n"
            "- Definida a inicialização padrão do sistema no modo Escuro (Dark).\n"
            "- Modificado o comportamento do tema para aplicar as alterações apenas após salvar as configurações.\n\n"
            "=== Versão 1.1.7  ===\n"
            "- Adicionados controles de 'Pausar' / 'Retomar' e 'Cancelar' para o fluxo de download.\n"
            "- Adicionado travamento de navegação lateral durante a execução do download para evitar inconsistências e congelamentos.\n"
            "- Implementado descarte automático de arquivos parciais corrompidos quando o download é cancelado.\n\n"
            "=== Versão 1.1.6  ===\n"
            "- Adicionada flag na tela de download para compactar a pasta de backup (.zip) com compressão máxima (nível 9).\n"
            "- Adicionada flag para excluir a pasta original de backup após a compactação ser concluída com sucesso.\n\n"
            "=== Versão 1.1.5  ===\n"
            "- Implementado tratamento de arquivos bloqueados/em uso no destino durante cópia (renomeação automática com timestamp milissegundos).\n\n"
            "=== Versão 1.1.4  ===\n"
            "- Ajustado o destino das marcas/interfaces para a raiz da pasta 'Modulos' (removendo subpastas 'interfaces/').\n"
            "- Ajustado o monitoramento de scripts: monitora se o executável principal inicia automaticamente o 'NBSScriptsRun.exe'.\n"
            "- Implementada espera automática de término do validador se detectado em execução, com fallback manual caso contrário.\n\n"
            "=== Versão 1.1.3  ===\n"
            "- Atualizado fluxo de execução do banco: agora executa o script principal e, ao término, executa o validador 'NBSScriptsRun.exe'.\n"
            "- Implementada verificação de existência e término síncrono para ambos os processos antes de reportar a conclusão.\n\n"
            "=== Versão 1.1.2  ===\n"
            "- Criada aba de 'Configurações' dedicada para edição e gravação manual dos parâmetros do config.json.\n"
            "- Simplificada a aba de 'Download & Backup' com a remoção de inputs estáticos e adição de painel informativo de caminhos ativos.\n"
            "- Adicionados campos de edição gráfica para os parâmetros de banco de dados (User, Pass, Schema, Service Name).\n\n"
            "=== Versão 1.1.1  ===\n"
            "- Adicionada a chave 'db_name' (Service Name do banco) nas configurações (config.json) e na interface.\n"
            "- Ajustada a geração de 'site.xml': agora preenche <db_name> com o Service Name e <host> com o Schema/Host.\n"
            "- Atualizados os campos id_site e descricao no arquivo 'site.xml' para fixar o valor 'NBS'.\n\n"
            "=== Versão 1.1.0  ===\n"
            "- Redesenho completo do Layout: Substituído o menu superior por navegação vertical na barra lateral esquerda.\n"
            "- Adicionada a aba 'Sobre o App' integrada para exibição de versão, contatos e histórico de alterações.\n"
            "- Implementado download compulsório da pasta de interfaces/especificas do FTP (respeitando a data de corte).\n\n"
            "=== Versão 1.0.0  ===\n"
            "- Backup automatizado dos executáveis locais (.exe) antes de realizar downloads.\n"
            "- Conexão FTP inteligente para verificação de data de modificação de arquivos (comando MDTM).\n"
            "- Cálculo automático da data da última atualização a partir do histórico de diretórios.\n"
            "- Execução elevada (UAC como Administrador) do script do banco com espera síncrona de término (UAC via ctypes).\n"
            "- Adicionado controle portátil de múltiplos servidores para distribuição de rede.\n"
            "- Download interativo de marcas com filtro de pesquisa e seleção múltipla.\n"
            "- Download do instalador NFE e script de transição de ano.\n"
            "- Adicionada flag de Instalação Inicial que baixa todas as DLLs e ignora a data de corte.\n"
            "- Detecção automática do S.O. com emulação (mocks) no Linux para testes locais do fluxo."
        )
        self.changelog_box.insert("0.0", changelog_text)
        self.changelog_box.configure(state="disabled")

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

        linx_changelog_text = (
            "=== Versão 1.1.0 ===\n"
            "- Adicionada opção de backup dos executáveis (.exe) e bibliotecas (.dll) da pasta C:\\Apollo\\atualiza antes da descompactação.\n"
            "- Adicionada flag na seleção de pacotes para ativar/desativar o backup do Apollo.\n"
            "- A pasta de backup do Apollo agora é gerada dinamicamente contendo a data no nome (ex: backup_DDMMYYYY).\n"
            "- Adicionada opção no menu de Serviços do Windows para encerrar processos do ApolloServer (powershell stop-process -name *serverapp*).\n"
            "- Suporte ao encerramento de processos executáveis ativos (como wsContabil.exe) por padrão Regex ou nome via PowerShell.\n"
            "- Limpeza e exclusão automática dos arquivos zipados (.zip) da pasta C:\\atualizacao após a descompactação e cópia dos arquivos.\n\n"
            "=== Versão 1.0.9 ===\n"
            "- Corrigido problema de detecção de status de serviços do Windows (DFeServico, etc.) em sistemas operacionais em outros idiomas (como Português-BR) adaptando a leitura para múltiplos padrões de resposta do comando 'sc query'.\n\n"
            "=== Versão 1.0.8 ===\n"
            "- Adicionado o novo Utilitário de Limpeza por Extensão na aba Linx, permitindo a pesquisa e remoção de arquivos de qualquer extensão customizada (.log, .tmp, .zip, etc.).\n\n"
            "=== Versão 1.0.7 ===\n"
            "- Adicionada opção para download do Linx DMS Integrador (arquivo LinxDMSIntegrador.zip) e monitoramento do serviço dmLDIServer.\n"
            "- Ajustadas pastas padrão do utilitário de exclusão Linx para C:\\Apollo e C:\\3camadas, e adicionado botão de busca para pasta customizada.\n"
            "- Implementada criptografia simétrica (XOR + Base64) das configurações locais gravadas em Appdata/Roaming ou ~/.config/AtualizadorSistemas/config.enc.\n"
            "- Integrada descompactação e execução elevada como Administrador para arquivos .exe e .msi internos do Integrador.\n\n"
            "=== Versão 1.0.6 ===\n"
            "- Adicionada aba 'Utilitários Linx' com exclusão de arquivos executáveis (.exe) e bibliotecas (.dll).\n"
            "- Suporte a filtros de pesquisa inteligentes com padrões Glob (ex: *2026*.dll) e Expressões Regulares (Regex).\n"
            "- Criado painel de monitoramento e controle assíncrono para os Serviços do Windows (DFeServico, RedirecionaDatasnap, VerificaServer3Camadas).\n"
            "- Implementado fluxo automatizado de descompactação e movimentação de arquivos nos diretórios corretos (Apollo/Atualiza, 3Camadas Server/Client).\n"
            "- Suporte para execução do Instalador Web (.exe/.msi) com privilégios de Administrador.\n"
            "- Corrigidos problemas de segurança de threads (TclError) ao atualizar status de serviços de forma assíncrona.\n"
            "- Ajustado tamanho e alinhamento dos cards na tela inicial (350px de largura com ancoragem de textos à esquerda).\n\n"
            "=== Versão 1.0.5 ===\n"
            "- Configuração de valores padrão para versão (5.19) e caminhos de atualização (C:\\atualizacao no Windows e /home/robson.santos@DTACENTER.MR/Dev/AtualizadorNBS no Linux).\n"
            "- Salvamento automático de versão e caminho ao perder o foco (FocusOut), pressionar Enter (Return) ou ao fechar o programa.\n"
            "- Corrigido problema de carregamento de interface que sobrescrevia as configurações com campos vazios na inicialização.\n"
            "- Implementação de aba dedicada 'Sobre o Linx' com changelog e documentação específica.\n\n"
            "=== Versão 1.0.4 ===\n"
            "- Criação da aba de Configurações Linx para customização dinâmica de todos os templates de URL (HTTP).\n"
            "- Correção de layout e compatibilização de temas (Light/Dark) na interface Linx.\n\n"
            "=== Versão 1.0.3 ===\n"
            "- Integração do controle de pausa ('Pausar' / 'Retomar') e cancelamento do download de pacotes Linx.\n"
            "- Bloqueio completo de campos e botões da aba Linx durante o andamento do processo de download.\n\n"
            "=== Versão 1.0.2 ===\n"
            "- Adicionado suporte para múltiplos tipos de pacotes/marcas Linx: LINXDMS, HPE, BRAVOS, TOYOTA.\n"
            "- Correção na formatação da versão, adicionando o prefixo 'v' automaticamente quando ausente.\n\n"
            "=== Versão 1.0.1 ===\n"
            "- Adicionado suporte a pacotes de 3 Camadas (Server / Client) e instalador Web completo.\n"
            "- Implementação de progresso visual (barra de progresso) e console de log em tempo real para downloads HTTP.\n\n"
            "=== Versão 1.0.0 ===\n"
            "- Implementação inicial da aba de Downloads do Linx DMS.\n"
            "- Suporte para download do pacote Delphi (Padrão) via HTTP.\n"
            "- Seleção de múltiplos pacotes adicionais: DMS Comissões, Apoio (Troca Fornecedor, Troca Série, Verifica Diária).\n"
            "- Preenchimento inteligente de URLs com substituição dinâmica de versão e tipo de pacote."
        )
        self.linx_changelog_box.insert("0.0", linx_changelog_text)
        self.linx_changelog_box.configure(state="disabled")

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
    def on_toggle_download_interfaces(self):
        self.save_ui_to_config()
        if self.download_interfaces_var.get():
            self.fetch_brands()
        else:
            # Hide list, show placeholder
            self.brands_scroll_frame.grid_forget()
            self.brands_loading_label.grid(row=1, column=0, pady=10)
            self.brands_loading_label.configure(text="Marcar a flag para carregar marcas do FTP...")

    def on_toggle_initial_installation(self):
        self.save_ui_to_config()
        if self.initial_installation_var.get():
            self.cutoff_date_entry.configure(state="disabled")
            self.log_to_dl_console("Modo 'Instalação Inicial' selecionado. A data de corte será ignorada para os módulos e todos os arquivos da pasta /dll serão baixados.")
        else:
            self.cutoff_date_entry.configure(state="normal")
            self.auto_detect_cutoff_date()

    def fetch_brands(self):
        """Launches background thread to get directories from the FTP interfaces folder."""
        self.brands_scroll_frame.grid_forget()
        self.brands_loading_label.grid(row=1, column=0, pady=10)
        self.brands_loading_label.configure(text="Conectando ao FTP para listar marcas...")
        
        threading.Thread(target=self._fetch_brands_thread, daemon=True).start()

    def _fetch_brands_thread(self):
        try:
            url = self.ftp_interfaces_entry.get()
            user = self.ftp_user_entry.get()
            pwd = self.ftp_pass_entry.get()
            
            host, port, path = ftp_client.parse_ftp_url(url)
            
            with ftp_client.FTPClient(host, port, user, pwd) as client:
                subdirs = client.list_subdirs(path)
                
            self.after(0, lambda: self.on_brands_fetched_success(subdirs))
        except Exception as e:
            self.after(0, lambda: self.on_brands_fetched_failed(str(e)))

    def on_brands_fetched_success(self, subdirs):
        self.brands_list = subdirs
        self.brands_loading_label.grid_forget()
        self.brands_scroll_frame.grid(row=1, column=0, rowspan=2, pady=5, sticky="nsew")
        
        # Clear existing scroll frame checkboxes
        for widget in self.brands_scroll_frame.winfo_children():
            widget.destroy()
            
        self.brand_checkboxes.clear()
        self.brand_widgets_in_grid.clear()
        
        saved_selected = self.app_config.get("selected_interfaces", [])
        
        # Populate checkboxes
        for i, brand in enumerate(subdirs):
            var = ctk.BooleanVar()
            if brand in saved_selected:
                var.set(True)
            check = ctk.CTkCheckBox(self.brands_scroll_frame, text=brand, variable=var, command=self.save_ui_to_config)
            check.grid(row=i, column=0, padx=10, pady=4, sticky="w")
            self.brand_checkboxes[brand] = check
            self.brand_widgets_in_grid.append((brand, check))
            
        self.log_to_dl_console(f"Carregadas {len(subdirs)} marcas do FTP de interfaces.")

    def on_brands_fetched_failed(self, error_msg):
        self.brands_loading_label.configure(text="Erro ao carregar marcas!")
        self.log_to_dl_console(f"Erro ao listar marcas no FTP de interfaces: {error_msg}")
        messagebox.showerror("Erro de Rede", f"Não foi possível conectar ao FTP de marcas:\n{error_msg}")

    def filter_brands_list(self, event=None):
        query = self.brands_search_entry.get().strip().lower()
        
        # Remove all from grid first
        for _, check in self.brand_widgets_in_grid:
            check.grid_forget()
            
        # Re-grid only matching ones
        row_idx = 0
        for brand, check in self.brand_widgets_in_grid:
            if not query or query in brand.lower():
                check.grid(row=row_idx, column=0, padx=10, pady=4, sticky="w")
                row_idx += 1

    # ----------------- DOWNLOAD & BACKUP TASK RUNNER -----------------
    def start_download_process(self):
        # Save UI current state
        self.save_ui_to_config()

        # Validations
        date_str = self.cutoff_date_entry.get().strip()
        cutoff_date = None
        if date_str:
            try:
                cutoff_date = datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Data Inválida", "Preencha a data de corte no formato correto (DD/MM/AAAA) ou limpe o campo.")
                return

        # Setup state flags
        self.download_paused = False
        self.download_cancelled = False
        self.current_downloading_file = None

        # Lock navigation and show pause/cancel buttons
        self.set_navigation_state("disabled")
        self.set_download_inputs_state("disabled")
        self.show_running_buttons()

        self.console_log.delete("1.0", "end")
        self.dl_progressbar.set(0)

        # Launch thread
        threading.Thread(target=self._download_process_thread, args=(cutoff_date,), daemon=True).start()

    def _download_process_thread(self, cutoff_date):
        def log(msg):
            self.after(0, lambda: self.log_to_dl_console(msg))
            
        def status(text):
            self.after(0, lambda: self.dl_status_label.configure(text=text))

        def check_pause_and_cancel():
            import time
            while self.download_paused:
                time.sleep(0.1)
                if self.download_cancelled:
                    raise Exception("Processo cancelado pelo usuário.")
            if self.download_cancelled:
                raise Exception("Processo cancelado pelo usuário.")

        def progress_callback(dl_bytes, total_bytes):
            check_pause_and_cancel()
            if total_bytes > 0:
                pct = dl_bytes / total_bytes
                self.after(0, lambda: self.dl_progressbar.set(pct))

        def download_with_control(client_inst, r_file, l_file, size):
            check_pause_and_cancel()
            
            # Check if file already exists and is identical (by hash or size fallback)
            if os.path.exists(l_file):
                local_size = os.path.getsize(l_file)
                if local_size == size:
                    # Try MD5 hash comparison first
                    remote_md5 = client_inst.get_file_md5(r_file)
                    if remote_md5:
                        local_md5 = utils.calculate_local_md5(l_file)
                        if local_md5 == remote_md5:
                            log(f"Arquivo {os.path.basename(l_file)} já baixado (hash OK). Pulando.")
                            self.after(0, lambda: self.dl_progressbar.set(1.0))
                            return
                        else:
                            log(f"Arquivo {os.path.basename(l_file)} tem tamanho igual mas hash diferente. Baixando novamente.")
                    else:
                        # Fallback to size consistency if server doesn't support MD5
                        log(f"Arquivo {os.path.basename(l_file)} já baixado (tamanho OK, servidor sem MD5). Pulando.")
                        self.after(0, lambda: self.dl_progressbar.set(1.0))
                        return

            self.current_downloading_file = l_file
            client_inst.download_file(r_file, l_file, progress_callback, size)
            check_pause_and_cancel()
            self.current_downloading_file = None

        try:
            c = self.app_config
            today_str = datetime.now().strftime("%d%m%Y")
            
            # Setup paths
            atualiza_path = c["atualizacao_path_win"] if self.os_type == "Windows" else c["atualizacao_path_linux"]
            nbs_path = c["nbs_path_win"] if self.os_type == "Windows" else c["nbs_path_linux"]
            
            base_dir = os.path.join(atualiza_path, today_str)
            backup_dir = os.path.join(base_dir, "backup")
            modules_dir = os.path.join(base_dir, "Modulos")

            os.makedirs(base_dir, exist_ok=True)

            log("--- INICIANDO PROCESSO ---")
            log(f"Pasta de atualização do dia: {base_dir}")

            # 1. LOCAL BACKUP
            compress_enabled = c.get("compress_backup", False)
            if utils.is_backup_up_to_date(nbs_path, backup_dir, compress_enabled):
                log("Backup já existente e idêntico à pasta local. Pulando backup.")
            else:
                status("Fazendo backup de executáveis locais...")
                backup_success = utils.backup_local_executables(nbs_path, backup_dir, log)

                if backup_success and compress_enabled:
                    status("Compactando pasta de backup...")
                    zip_path = utils.compress_folder(backup_dir, 'zip', log)
                    if zip_path and c.get("delete_backup_after_compress", False):
                        status("Removendo pasta de backup original...")
                        try:
                            shutil.rmtree(backup_dir)
                            log("Pasta de backup original removida com sucesso.")
                        except Exception as rm_err:
                            log(f"Erro ao remover pasta de backup original: {str(rm_err)}")

            # Check for Initial Installation flag
            if c.get("initial_installation", False):
                cutoff_date = None
                log("Modo 'Instalação Inicial' ativado. A data de corte será ignorada para módulos e marcas.")

            # 2. DOWNLOAD MODULES
            status("Conectando ao FTP de Módulos...")
            m_host, m_port, m_path = ftp_client.parse_ftp_url(c["ftp_modules_url"])
            
            with ftp_client.FTPClient(m_host, m_port, c["ftp_user"], c["ftp_password"]) as client:
                log("Conectado no FTP com sucesso.")
                
                # Fetch files
                status("Obtendo listagem de módulos...")
                files = client.list_files_with_info(m_path)
                
                # Filter modules by cut-off date
                files_to_download = []
                for f in files:
                    if f["modified"] is None:
                        # Fallback: if we can't determine modification date, download it
                        files_to_download.append(f)
                    elif cutoff_date is None or f["modified"] >= cutoff_date:
                        files_to_download.append(f)

                log(f"Total de módulos encontrados: {len(files)}")
                log(f"Módulos para download (após {cutoff_date.strftime('%d/%m/%Y') if cutoff_date else 'início'}): {len(files_to_download)}")

                for i, f in enumerate(files_to_download):
                    remote_file = f"{m_path.rstrip('/')}/{f['name']}"
                    local_file = os.path.join(modules_dir, f["name"])
                    
                    status(f"Baixando módulo ({i+1}/{len(files_to_download)}): {f['name']}")
                    log(f"Baixando {f['name']} (Modificação: {f['modified'].strftime('%d/%m/%Y %H:%M') if f['modified'] else 'Desconhecida'})")
                    
                    download_with_control(client, remote_file, local_file, f["size"])
                
                log("Módulos baixados.")

                # 2.2 DOWNLOAD interfaces/especificas (Always downloaded)
                log("Iniciando download dos módulos de interfaces/especificas...")
                status("Obtendo listagem de interfaces/especificas...")
                
                int_host, int_port, int_path = ftp_client.parse_ftp_url(c["ftp_interfaces_url"])
                especificas_remote_dir = f"{int_path.rstrip('/')}/especificas"
                especificas_local_dir = modules_dir
                
                esp_client = client
                own_esp_client = False
                if int_host != m_host or int_port != m_port:
                    esp_client = ftp_client.FTPClient(int_host, int_port, c["ftp_user"], c["ftp_password"])
                    esp_client.connect()
                    own_esp_client = True
                    
                try:
                    esp_files = esp_client.list_files_with_info(especificas_remote_dir)
                    esp_files_to_download = []
                    for ef in esp_files:
                        if ef["modified"] is None or cutoff_date is None or ef["modified"] >= cutoff_date:
                            esp_files_to_download.append(ef)
                            
                    log(f"Interfaces/especificas: {len(esp_files_to_download)} de {len(esp_files)} arquivos para download")
                    
                    for ei, ef in enumerate(esp_files_to_download):
                        r_esp_path = f"{especificas_remote_dir}/{ef['name']}"
                        l_esp_path = os.path.join(especificas_local_dir, ef["name"])
                        
                        status(f"Baixando especificas ({ei+1}/{len(esp_files_to_download)}): {ef['name']}")
                        download_with_control(esp_client, r_esp_path, l_esp_path, ef["size"])
                    log("Arquivos de interfaces/especificas baixados.")
                except Exception as esp_err:
                    log(f"Erro ao baixar interfaces/especificas: {str(esp_err)}")
                finally:
                    if own_esp_client:
                        esp_client.disconnect()

                # 2.5 DOWNLOAD DLLs (if initial_installation is checked)
                if c.get("initial_installation", False):
                    log("Iniciando download das DLLs em /sistemadelphi/modulos/dll...")
                    status("Conectando ao FTP de DLLs...")
                    dll_host, dll_port, dll_path = ftp_client.parse_ftp_url(c.get("ftp_dll_url", "ftp://nbsi.com.br/sistemadelphi/modulos/dll"))
                    
                    dll_client = client
                    own_dll_client = False
                    if dll_host != m_host or dll_port != m_port:
                        dll_client = ftp_client.FTPClient(dll_host, dll_port, c["ftp_user"], c["ftp_password"])
                        dll_client.connect()
                        own_dll_client = True
                    
                    try:
                        status("Obtendo listagem de DLLs...")
                        dll_files = dll_client.list_files_with_info(dll_path)
                        log(f"Encontrados {len(dll_files)} arquivos de DLL para baixar.")
                        
                        for di, df in enumerate(dll_files):
                            r_dll_path = f"{dll_path.rstrip('/')}/{df['name']}"
                            l_dll_path = os.path.join(modules_dir, df["name"])
                            
                            status(f"Baixando DLL ({di+1}/{len(dll_files)}): {df['name']}")
                            download_with_control(dll_client, r_dll_path, l_dll_path, df["size"])
                        log("Todos os arquivos de DLL foram baixados.")
                    finally:
                        if own_dll_client:
                            dll_client.disconnect()

                # 3. DOWNLOAD BRANDS (INTERFACES)
                if c["download_interfaces"] and c["selected_interfaces"]:
                    log("Iniciando download de interfaces de marcas...")
                    int_host, int_port, int_path = ftp_client.parse_ftp_url(c["ftp_interfaces_url"])
                    
                    for brand in c["selected_interfaces"]:
                        log(f"Processando marca: {brand}")
                        status(f"Buscando arquivos da marca: {brand}")
                        
                        brand_remote_dir = f"{int_path.rstrip('/')}/{brand}"
                        brand_local_dir = modules_dir
                        
                        brand_files = client.list_files_with_info(brand_remote_dir)
                        brand_files_to_download = []
                        for bf in brand_files:
                            if bf["modified"] is None or cutoff_date is None or bf["modified"] >= cutoff_date:
                                brand_files_to_download.append(bf)
                                
                        log(f"Marca {brand}: {len(brand_files_to_download)} de {len(brand_files)} arquivos para download")
                        
                        for bi, bf in enumerate(brand_files_to_download):
                            r_path = f"{brand_remote_dir}/{bf['name']}"
                            l_path = os.path.join(brand_local_dir, bf["name"])
                            
                            status(f"Baixando {brand} ({bi+1}/{len(brand_files_to_download)}): {bf['name']}")
                            download_with_control(client, r_path, l_path, bf["size"])

                # 4. DOWNLOAD SCRIPTS
                log("Conectando ao FTP de Scripts...")
                sc_host, sc_port, sc_path = ftp_client.parse_ftp_url(c["ftp_scripts_url"])
                
                # Check for other client instance if host is different (re-connect if needed, or re-use if same)
                script_client = client
                own_client = False
                if sc_host != m_host or sc_port != m_port:
                    script_client = ftp_client.FTPClient(sc_host, sc_port, c["ftp_user"], c["ftp_password"])
                    script_client.connect()
                    own_client = True

                try:
                    status("Buscando script mais recente...")
                    script_files = script_client.list_files_with_info(sc_path)
                    
                    # Filter matching NBSScripts_X.Y.Z.W.exe
                    # Do not match transition year formats like NBSScripts_2025.exe unless version matches.
                    # We can use regex to find versioned scripts
                    versioned_scripts = []
                    version_pattern = re.compile(r'^NBSScripts_\d+\.\d+\.\d+\.\d+\.exe$', re.IGNORECASE)
                    
                    for sf in script_files:
                        if version_pattern.match(sf["name"]):
                            versioned_scripts.append(sf)
                            
                    # Sort versioned scripts by modification time descending
                    if versioned_scripts:
                        # Sort by modification date
                        versioned_scripts.sort(key=lambda x: x["modified"] or datetime.min, reverse=True)
                        newest_script = versioned_scripts[0]
                        
                        log(f"Script mais recente identificado: {newest_script['name']}")
                        status(f"Baixando script: {newest_script['name']}")
                        
                        remote_sc = f"{sc_path.rstrip('/')}/{newest_script['name']}"
                        local_sc = os.path.join(base_dir, newest_script["name"])
                        
                        download_with_control(script_client, remote_sc, local_sc, newest_script["size"])
                        log(f"Script {newest_script['name']} baixado.")
                        
                        # Cache path of the script for the Exec tab
                        self.latest_downloaded_script = os.path.normpath(local_sc)
                        self.after(0, self.auto_fill_script_runner_path)
                    else:
                        log("Nenhum script versionado (NBSScripts_X.X.X.X.exe) encontrado no FTP de scripts.")

                    # Year Transition Script
                    if c["transition_year_enabled"] and c["transition_year_value"]:
                        year = c["transition_year_value"]
                        target_name = f"NBSScripts_{year}.exe"
                        
                        # Find in files
                        found_transition_file = None
                        for sf in script_files:
                            if sf["name"].lower() == target_name.lower():
                                found_transition_file = sf
                                break
                                
                        if found_transition_file:
                            log(f"Script de transição {target_name} encontrado. Iniciando download...")
                            status(f"Baixando script de transição: {target_name}")
                            
                            remote_sc = f"{sc_path.rstrip('/')}/{found_transition_file['name']}"
                            local_sc = os.path.join(base_dir, found_transition_file["name"])
                            
                            download_with_control(script_client, remote_sc, local_sc, found_transition_file["size"])
                            log(f"Script de transição {target_name} baixado.")
                        else:
                            log(f"Alerta: Script de transição {target_name} NÃO encontrado no FTP de scripts.")

                finally:
                    if own_client:
                        script_client.disconnect()

                # 5. DOWNLOAD NFE
                if c["download_nfe"]:
                    log("Conectando ao FTP NFE...")
                    nfe_host, nfe_port, nfe_path = ftp_client.parse_ftp_url(c["ftp_nfe_url"])
                    
                    nfe_client = client
                    own_nfe_client = False
                    if nfe_host != m_host or nfe_port != m_port:
                        nfe_client = ftp_client.FTPClient(nfe_host, nfe_port, c["ftp_user"], c["ftp_password"])
                        nfe_client.connect()
                        own_nfe_client = True
                        
                    try:
                        status("Buscando instalador NFE...")
                        nfe_files = nfe_client.list_files_with_info(nfe_path)
                        
                        nfe_installers = []
                        nfe_pattern = re.compile(r'^InstaladorNFE_.*\.exe$', re.IGNORECASE)
                        for nf in nfe_files:
                            if nfe_pattern.match(nf["name"]):
                                nfe_installers.append(nf)
                                
                        if nfe_installers:
                            # Sort by modification time
                            nfe_installers.sort(key=lambda x: x["modified"] or datetime.min, reverse=True)
                            newest_nfe = nfe_installers[0]
                            
                            log(f"Instalador NFE mais recente identificado: {newest_nfe['name']}")
                            status(f"Baixando NFE: {newest_nfe['name']}")
                            
                            remote_nfe = f"{nfe_path.rstrip('/')}/{newest_nfe['name']}"
                            local_nfe = os.path.join(base_dir, newest_nfe["name"])
                            
                            download_with_control(nfe_client, remote_nfe, local_nfe, newest_nfe["size"])
                            log(f"Instalador NFE {newest_nfe['name']} baixado.")
                        else:
                            log("Nenhum instalador NFE (InstaladorNFE_*.exe) encontrado.")
                    finally:
                        if own_nfe_client:
                            nfe_client.disconnect()

                # 6. CREATE site.xml (If initial_installation is checked)
                if c.get("initial_installation", False):
                    log("Instalação Inicial: Gerando arquivo site.xml...")
                    xml_content = f"""<?xml version="1.0" ?>
<sites>
	<site>
		<id_site>NBS</id_site>
		<descricao>NBS</descricao>
		<db_type>Oracle</db_type>
		<user>{c.get('db_user', '')}</user>
		<pass>{c.get('db_password', '')}</pass>
		<db_name>{c.get('db_name', '')}</db_name>
		<host>{c.get('db_schema', '')}</host>
	</site>
</sites>
"""
                    xml_file_path = os.path.join(modules_dir, "site.xml")
                    try:
                        with open(xml_file_path, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        log(f"Arquivo site.xml gerado com sucesso em: {xml_file_path}")
                    except Exception as xml_err:
                        log(f"Erro ao gerar site.xml: {str(xml_err)}")

            log("--- PROCESSO CONCLUÍDO ---")
            status("Processo finalizado com sucesso!")
            self.after(0, lambda: self.dl_progressbar.set(1.0))
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Download e Backup concluídos com sucesso!"))
            
        except Exception as e:
            if str(e) == "Processo cancelado pelo usuário.":
                log("--- PROCESSO CANCELADO ---")
                status("Processo cancelado.")
                self.after(0, lambda: self.dl_progressbar.set(0))
                self.after(0, lambda: messagebox.showwarning("Cancelado", "O processo de download e backup foi cancelado pelo usuário."))
            else:
                log(f"ERRO CRÍTICO no processo: {str(e)}")
                status("Erro no processo.")
                self.after(0, lambda: self.dl_progressbar.set(0))
                self.after(0, lambda: messagebox.showerror("Erro no Processo", f"Ocorreu um erro durante a execução:\n{str(e)}"))
        finally:
            # Clean up active partial download if present
            if self.current_downloading_file and os.path.exists(self.current_downloading_file):
                try:
                    os.remove(self.current_downloading_file)
                    log(f"Arquivo parcial removido: {os.path.basename(self.current_downloading_file)}")
                except Exception as clean_err:
                    log(f"Erro ao limpar arquivo parcial: {str(clean_err)}")
            self.current_downloading_file = None

            # Restore UI controls
            self.after(0, self.show_idle_buttons)
            self.after(0, lambda: self.set_navigation_state("normal"))
            self.after(0, lambda: self.set_download_inputs_state("normal"))

    def auto_fill_script_runner_path(self):
        if self.latest_downloaded_script:
            self.script_path_entry.delete(0, "end")
            self.script_path_entry.insert(0, self.latest_downloaded_script)

    # ----------------- SCRIPT EXECUTION TASK RUNNER -----------------
    def start_script_execution(self):
        filepath = self.script_path_entry.get().strip()
        if not filepath:
            messagebox.showerror("Erro", "Selecione o arquivo de script NBS Scripts para executar.")
            return

        self.run_script_btn.configure(state="disabled")
        self.exec_status_label.configure(text="Status: Preparando execução...")
        self.exec_log_box.delete("1.0", "end")

        threading.Thread(target=self._script_execution_thread, args=(filepath,), daemon=True).start()

    def is_process_running(self, name):
        try:
            import subprocess
            if self.os_type == "Windows":
                # CREATE_NO_WINDOW = 0x08000000 to prevent terminal window flashing
                out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}"], capture_output=True, text=True, creationflags=0x08000000)
                return name.lower() in out.stdout.lower()
            else:
                out = subprocess.run(["ps", "ax"], capture_output=True, text=True)
                return name.lower() in out.stdout.lower()
        except Exception:
            return False

    def _script_execution_thread(self, filepath):
        def log(msg):
            self.after(0, lambda: self.log_to_exec_console(msg))
            
        def status(text):
            self.after(0, lambda: self.exec_status_label.configure(text=f"Status: {text}"))

        if self.os_type != "Windows":
            # Simulate both processes on Linux
            status("Executando Script (Simulação)...")
            log(f"Iniciando script principal (Simulação): {os.path.basename(filepath)}")
            time.sleep(2)
            log("[Linux SIMULADO] Script principal finalizado.")
            log("[Linux SIMULADO] Validador NBSScriptsRun.exe iniciado automaticamente.")
            time.sleep(2)
            log("[Linux SIMULADO] Validador NBSScriptsRun.exe finalizado.")
            status("Concluído.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Script de banco e validador NBSScriptsRun.exe executados e finalizados com sucesso!"))
            self.after(0, lambda: self.run_script_btn.configure(state="normal"))
            return

        status("Executando Script...")
        log(f"Iniciando script de banco principal: {os.path.basename(filepath)}")
        
        success1 = utils.execute_script_as_admin(filepath, log)
        if not success1:
            status("Erro.")
            self.after(0, lambda: messagebox.showerror("Falha na Execução", "O script principal reportou erro ou foi cancelado pelo usuário."))
            self.after(0, lambda: self.run_script_btn.configure(state="normal"))
            return

        # Main script finished. Now monitor if NBSScriptsRun.exe is launched automatically.
        log("Script principal finalizado. Monitorando inicialização do validador NBSScriptsRun.exe...")
        status("Aguardando validador...")
        
        # Poll for up to 10 seconds to see if the versioned script has spawned it
        is_running = False
        for i in range(10):
            time.sleep(1)
            if self.is_process_running("NBSScriptsRun.exe"):
                is_running = True
                break
            if i % 3 == 0:
                log("Verificando se NBSScriptsRun.exe foi iniciado...")

        if is_running:
            log("Validador NBSScriptsRun.exe detectado em execução. Aguardando conclusão do processo...")
            status("Executando validador...")
            # Keep polling until it completes
            while self.is_process_running("NBSScriptsRun.exe"):
                time.sleep(2)
            log("Validador NBSScriptsRun.exe finalizado com sucesso.")
            status("Concluído.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Script de banco e validador NBSScriptsRun.exe executados e finalizados com sucesso!"))
        else:
            log("Alerta: O validador NBSScriptsRun.exe não foi iniciado automaticamente.")
            status("Concluído (Manual).")
            self.after(0, lambda: messagebox.showinfo(
                "Sucesso", 
                "Script principal executado com sucesso!\n\n"
                "Aviso: Favor proceder com a atualização Via NBS Scripts Run manualmente se necessário."
            ))
            
        self.after(0, lambda: self.run_script_btn.configure(state="normal"))

    # ----------------- DISTRIBUTION & SERVERS LIST UTILS -----------------
    def refresh_servers_list_ui(self):
        """Re-draws the list of servers in Tab 3 with Remove buttons next to them."""
        for widget in self.servers_scroll_frame.winfo_children():
            widget.destroy()

        servers = self.app_config.get("servers", [])
        
        if not servers:
            lbl = ctk.CTkLabel(self.servers_scroll_frame, text="Nenhum servidor cadastrado.", font=ctk.CTkFont(slant="italic"))
            lbl.grid(row=0, column=0, padx=10, pady=10, sticky="w")
            return

        for i, sv in enumerate(servers):
            # Row container
            row = ctk.CTkFrame(self.servers_scroll_frame, fg_color="transparent")
            row.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            
            lbl = ctk.CTkLabel(row, text=sv, anchor="w")
            lbl.grid(row=0, column=0, padx=5, pady=2, sticky="w")
            
            btn = ctk.CTkButton(row, text="Remover", width=60, fg_color="#c0392b", hover_color="#e74c3c", command=lambda s=sv: self.remove_server_from_list(s))
            btn.grid(row=0, column=1, padx=5, pady=2)

    def add_server_to_list(self):
        val = self.server_entry.get().strip()
        if not val:
            return

        # Ensure UNC formats or IP strings
        servers = self.app_config.get("servers", [])
        if val not in servers:
            servers.append(val)
            self.app_config["servers"] = servers
            self.save_ui_to_config()
            self.refresh_servers_list_ui()
            self.server_entry.delete(0, "end")
        else:
            messagebox.showwarning("Aviso", "Este servidor já está cadastrado.")

    def remove_server_from_list(self, server_value):
        servers = self.app_config.get("servers", [])
        if server_value in servers:
            servers.remove(server_value)
            self.app_config["servers"] = servers
            self.save_ui_to_config()
            self.refresh_servers_list_ui()

    def start_distribution_process(self):
        self.save_ui_to_config()
        
        copy_local = self.copy_local_var.get()
        copy_servers = self.copy_servers_var.get()
        servers = self.app_config.get("servers", [])

        if not copy_local and (not copy_servers or not servers):
            messagebox.showerror("Erro", "Selecione pelo menos uma opção de destino e garanta que existam servidores configurados.")
            return

        # Locate the local Modules folder to copy from (C:\Atualizacao\<today>\Modulos)
        c = self.app_config
        today_str = datetime.now().strftime("%d%m%Y")
        atualiza_path = c["atualizacao_path_win"] if self.os_type == "Windows" else c["atualizacao_path_linux"]
        
        source_modules_dir = os.path.join(atualiza_path, today_str, "Modulos")
        if not os.path.exists(source_modules_dir):
            messagebox.showerror("Erro", f"A pasta de módulos do dia de hoje não foi encontrada:\n{source_modules_dir}\nPor favor, execute o download na Aba 1 primeiro.")
            return

        self.start_dist_btn.configure(state="disabled")
        
        # Clear copy status frame and console log
        for widget in self.copy_status_frame.winfo_children():
            widget.destroy()

        self.dist_console_log.configure(state="normal")
        self.dist_console_log.delete("1.0", "end")
        self.dist_console_log.configure(state="disabled")

        self.dist_log_label.configure(text="Iniciando cópia das atualizações...")

        # Setup destinations dictionary: {name_to_display: actual_path}
        destinations = {}
        
        if copy_local:
            local_nbs = c["nbs_path_win"] if self.os_type == "Windows" else c["nbs_path_linux"]
            destinations["Local (C:\\NBS)"] = os.path.normpath(local_nbs)
            
        if copy_servers and servers:
            for s in servers:
                # If s is just an IP, format it to UNC path, otherwise use UNC as-is
                if not s.startswith("\\\\") and not s.startswith("//"):
                    unc_path = f"\\\\{s}\\c$\\NBS"
                else:
                    unc_path = s
                destinations[s] = unc_path

        threading.Thread(target=self._distribution_thread, args=(source_modules_dir, destinations), daemon=True).start()

    def _distribution_thread(self, source_dir, destinations):
        # Create UI labels for status tracking
        status_labels = {}
        row_idx = 0
        
        # Setup log file
        parent_dir = os.path.dirname(source_dir)
        log_file_path = os.path.join(parent_dir, "distribuicao.log")
        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== LOG DE DISTRIBUIÇÃO - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===\n\n")
        except Exception:
            pass

        def dist_log(msg):
            # Log to UI console
            self.after(0, lambda: self.log_to_dist_console(msg))
            # Log to file
            try:
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            except Exception:
                pass

        # Helper to schedule widget creation in main thread
        def create_status_row(name):
            row_frame = ctk.CTkFrame(self.copy_status_frame, fg_color="transparent")
            row_frame.grid(row=row_idx, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
            row_frame.grid_columnconfigure(0, weight=2)
            
            nlbl = ctk.CTkLabel(row_frame, text=name, anchor="w")
            nlbl.grid(row=0, column=0, padx=5, pady=2, sticky="w")
            
            slbl = ctk.CTkLabel(row_frame, text="Aguardando...", font=ctk.CTkFont(weight="bold"), text_color="gray")
            slbl.grid(row=0, column=1, padx=5, pady=2, sticky="e")
            
            status_labels[name] = slbl

        # Create status rows sequentially
        for name in destinations.keys():
            self.after(0, lambda n=name: create_status_row(n))
            row_idx += 1
            
        # Give UI a millisecond to draw rows
        time.sleep(0.1)

        def update_lbl(name, text, color):
            self.after(0, lambda: status_labels[name].configure(text=text, text_color=color))

        def log_text(text):
            self.after(0, lambda: self.dist_log_label.configure(text=text))
            dist_log(text)

        overall_success = True

        for name, dst_path in destinations.items():
            log_text(f"Distribuindo para {name}...")
            update_lbl(name, "Copiando...", "orange")
            
            # Run the actual utility copy function
            success = utils.distribute_to_destination(source_dir, dst_path, log_callback=dist_log)
            
            if success:
                update_lbl(name, "Sucesso", "green")
                dist_log(f"Sucesso na cópia para {name} ({dst_path})")
            else:
                update_lbl(name, "Falha", "red")
                dist_log(f"Falha na cópia para {name} ({dst_path})")
                overall_success = False

        log_text("Distribuição finalizada.")
        
        if overall_success:
            self.after(0, lambda: messagebox.showinfo("Distribuição Concluída", "Atualizações distribuídas para todos os locais com sucesso!"))
        else:
            self.after(0, lambda: messagebox.showwarning("Distribuição Parcial", "A distribuição foi finalizada, mas uma ou mais máquinas falharam na cópia. Verifique os status individuais."))

        self.after(0, lambda: self.start_dist_btn.configure(state="normal"))

    # ----------------- TABS & METHODS FOR LINX UPDATER -----------------
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

        # Title
        ctk.CTkLabel(tab, text="Utilitários e Manutenção Linx", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkLabel(tab, text="Ferramentas auxiliares para gerenciamento, pesquisa e limpeza de arquivos do Linx.", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

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

if __name__ == "__main__":
    # Ensure Tkinter runs correctly (handles X server issues gracefully on headless servers if needed)
    try:
        app = AtualizadorApp()
        app.mainloop()
    except Exception as e:
        print(f"Erro ao inicializar interface gráfica: {str(e)}")
        sys.exit(1)
