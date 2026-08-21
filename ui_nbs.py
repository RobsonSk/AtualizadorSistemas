import os
import sys
import re
import platform
import threading
import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QComboBox, QTextEdit,
    QProgressBar, QGroupBox, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QFrame, QHeaderView, QTableWidget, QTableWidgetItem
)

import config
import ftp_client
import utils
from changelog import CHANGELOG_NBS
from ui_common import CTkToolTip
from license_gatekeeper import LicenseManager, LicenseActivationDialog, get_hwid


def set_entry_text(widget, text):
    if widget is not None:
        widget.setText(str(text) if text is not None else "")


def get_entry_text(widget):
    if widget is not None:
        return widget.text().strip()
    return ""


class NBSMixin:
    """Interface, abas e lógica de negócios específica do sistema NBS usando PySide6."""

    def setup_tab_download(self):
        tab = self.frame_download
        layout = QHBoxLayout(tab)

        # Left Column (Parameters)
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_left.setWidget(left_widget)

        param_group = QGroupBox("Parâmetros de Execução")
        param_layout = QVBoxLayout(param_group)

        # Cut-off Date
        date_lbl = QLabel("Data de Corte (Última Atualização):")
        date_lbl.setStyleSheet("font-weight: bold;")
        date_row = QHBoxLayout()
        self.cutoff_date_entry = QLineEdit()
        self.cutoff_date_entry.setPlaceholderText("DD/MM/AAAA")
        self.recalc_btn = QPushButton("Recalcular")
        self.recalc_btn.clicked.connect(self.auto_detect_cutoff_date)
        date_row.addWidget(self.cutoff_date_entry, 1)
        date_row.addWidget(self.recalc_btn)

        param_layout.addWidget(date_lbl)
        param_layout.addLayout(date_row)

        # Recap paths
        recap_group = QGroupBox("Locais de Destino")
        recap_layout = QVBoxLayout(recap_group)
        self.recap_atualiza_lbl = QLabel("Atualização: -")
        self.recap_nbs_lbl = QLabel("NBS Local: -")
        self.recap_ftp_lbl = QLabel("FTP: -")
        recap_layout.addWidget(self.recap_atualiza_lbl)
        recap_layout.addWidget(self.recap_nbs_lbl)
        recap_layout.addWidget(self.recap_ftp_lbl)
        param_layout.addWidget(recap_group)

        # Checkboxes Group
        opts_group = QGroupBox("Pacotes e Opções de Download")
        opts_layout = QVBoxLayout(opts_group)

        self.download_nbs_var = QCheckBox("Módulos Oficiais NBS")
        self.download_nbs_var.setChecked(True)
        self.download_scripts_var = QCheckBox("Scripts de Banco de Dados")
        self.download_scripts_var.setChecked(True)
        self.download_interfaces_var = QCheckBox("Interfaces de Marcas")
        self.download_interfaces_var.stateChanged.connect(self.on_toggle_interfaces)
        self.download_nfe_var = QCheckBox("Módulo NFE")
        self.initial_installation_var = QCheckBox("Instalação Inicial (Baixar Tudo / Ignorar Data de Corte)")
        self.initial_installation_var.stateChanged.connect(self.on_toggle_initial_installation)
        self.compress_backup_var = QCheckBox("Compactar pastas de backup (.zip)")
        self.delete_backup_after_compress_var = QCheckBox("Excluir pasta de backup descompactada após gerar .zip")
        self.debug_mode_var = QCheckBox("Modo Debug (Exibir Logs Detalhados de FTP e Conexões)")

        opts_layout.addWidget(self.download_nbs_var)
        opts_layout.addWidget(self.download_scripts_var)
        opts_layout.addWidget(self.download_interfaces_var)
        opts_layout.addWidget(self.download_nfe_var)
        opts_layout.addWidget(self.initial_installation_var)
        opts_layout.addWidget(self.compress_backup_var)
        opts_layout.addWidget(self.delete_backup_after_compress_var)
        opts_layout.addWidget(self.debug_mode_var)
        param_layout.addWidget(opts_group)


        # Brands Group
        self.brands_group = QGroupBox("Interfaces de Marcas para Download")
        self.brands_group_layout = QVBoxLayout(self.brands_group)

        # Search / Filter & Selection Control Row
        filter_row = QHBoxLayout()
        self.brand_search_entry = QLineEdit()
        self.brand_search_entry.setPlaceholderText("🔍 Pesquisar marca de interface...")
        self.brand_search_entry.textChanged.connect(self.filter_brands)

        btn_select_all = QPushButton("Marcar Todas")
        btn_select_all.setStyleSheet("padding: 4px 8px;")
        btn_select_all.clicked.connect(lambda: self.set_all_brands_checked(True))

        btn_deselect_all = QPushButton("Desmarcar Todas")
        btn_deselect_all.setStyleSheet("padding: 4px 8px;")
        btn_deselect_all.clicked.connect(lambda: self.set_all_brands_checked(False))

        filter_row.addWidget(self.brand_search_entry, 1)
        filter_row.addWidget(btn_select_all)
        filter_row.addWidget(btn_deselect_all)
        self.brands_group_layout.addLayout(filter_row)

        # Status Label
        self.brands_status_lbl = QLabel("Clique em 'Interfaces de Marcas' para carregar do FTP.")
        self.brands_status_lbl.setStyleSheet("font-style: italic; color: #aaa; margin: 4px 0px;")
        self.brands_group_layout.addWidget(self.brands_status_lbl)

        self.brands_scroll = QScrollArea()
        self.brands_scroll.setWidgetResizable(True)
        self.brands_scroll.setMinimumHeight(200)
        self.brands_scroll.setMaximumHeight(280)
        self.brands_scroll.setStyleSheet("QScrollArea { background-color: #11111b; border: 1px solid #45475a; border-radius: 6px; }")

        self.brands_content = QWidget()
        self.brands_content.setStyleSheet("background-color: #11111b;")
        self.brands_layout = QVBoxLayout(self.brands_content)
        self.brands_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.brands_layout.setContentsMargins(8, 8, 8, 8)
        self.brands_layout.setSpacing(4)
        self.brands_scroll.setWidget(self.brands_content)

        self.brands_group_layout.addWidget(self.brands_scroll)
        self.brand_checkboxes = {}
        param_layout.addWidget(self.brands_group)


        # Sync initial state of brands group
        self.on_toggle_interfaces()

        left_layout.addWidget(param_group)




        # Right Column (Logs & Action)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.dl_status_label = QLabel("Status: Aguardando início do processo...")
        self.dl_status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #3498db;")

        self.dl_progressbar = QProgressBar()
        self.dl_progressbar.setRange(0, 100)
        self.dl_progressbar.setValue(0)

        self.dl_log_box = QTextEdit()
        self.dl_log_box.setReadOnly(True)
        self.dl_log_box.setStyleSheet("font-family: monospace; font-size: 11px;")

        btn_row = QHBoxLayout()
        self.btn_run_download = QPushButton("Iniciar Download e Atualização")
        self.btn_run_download.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_download.clicked.connect(self.run_download_process)

        self.btn_pause_download = QPushButton("Pausar")
        self.btn_pause_download.setEnabled(False)
        self.btn_pause_download.clicked.connect(self.pause_download_process)

        self.btn_cancel_download = QPushButton("Cancelar")
        self.btn_cancel_download.setEnabled(False)
        self.btn_cancel_download.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        self.btn_cancel_download.clicked.connect(self.cancel_download_process)

        btn_row.addWidget(self.btn_run_download, 2)
        btn_row.addWidget(self.btn_pause_download, 1)
        btn_row.addWidget(self.btn_cancel_download, 1)

        right_layout.addWidget(self.dl_status_label)
        right_layout.addWidget(self.dl_progressbar)
        right_layout.addWidget(self.dl_log_box, 1)
        right_layout.addLayout(btn_row)

        layout.addWidget(scroll_left, 1)
        layout.addWidget(right_widget, 1)

    def setup_tab_execution(self):
        tab = self.frame_execution
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 1. Header
        lbl_title = QLabel("Executar Script de Banco de Dados")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        lbl_subtitle = QLabel("Selecione o arquivo de script NBS Scripts baixado para rodar as atualizações no banco.")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)

        # 2. File Selection Bar
        file_group = QGroupBox("Arquivo de Script (.exe)")
        file_layout = QHBoxLayout(file_group)
        self.script_path_entry = QLineEdit()
        self.script_path_entry.setPlaceholderText("Selecione o arquivo executável (ex: NBSScripts_1.57.95.41.exe)...")
        btn_browse_script = QPushButton("Procurar...")
        btn_browse_script.setFixedWidth(100)
        btn_browse_script.clicked.connect(self.browse_script_file)
        file_layout.addWidget(self.script_path_entry, 1)
        file_layout.addWidget(btn_browse_script)
        layout.addWidget(file_group)

        # 3. DB Credentials Panel
        db_group = QGroupBox("Parâmetros de Banco de Dados (config.json)")
        db_layout = QVBoxLayout(db_group)

        db_grid = QGridLayout()
        self.db_user_lbl = QLabel("Usuário: ••••••••")
        self.db_schema_lbl = QLabel("Schema/Host: ••••••••")
        self.db_name_lbl = QLabel("Service Name: ••••••••")
        self.db_pass_lbl = QLabel("Senha: ••••••••")

        self.db_user_lbl.setStyleSheet("color: #cdd6f4;")
        self.db_schema_lbl.setStyleSheet("color: #cdd6f4;")
        self.db_name_lbl.setStyleSheet("color: #cdd6f4;")
        self.db_pass_lbl.setStyleSheet("color: #cdd6f4;")

        db_grid.addWidget(self.db_user_lbl, 0, 0)
        db_grid.addWidget(self.db_schema_lbl, 0, 1)
        db_grid.addWidget(self.db_name_lbl, 1, 0)
        db_grid.addWidget(self.db_pass_lbl, 1, 1)
        db_layout.addLayout(db_grid)

        self.db_toggle_btn = QPushButton("Exibir Credenciais")
        self.db_toggle_btn.setFixedWidth(150)
        self.db_toggle_btn.clicked.connect(self.toggle_db_credentials)
        db_layout.addWidget(self.db_toggle_btn)

        self.db_credentials_visible = False
        layout.addWidget(db_group)

        # 4. Action Execution Button
        self.run_script_btn = QPushButton("🚀 Executar como Administrador")
        self.run_script_btn.setStyleSheet("""
            QPushButton {
                background-color: #d35400;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #585b70;
                color: #a6adc8;
            }
        """)
        self.run_script_btn.clicked.connect(self.start_script_execution)
        layout.addWidget(self.run_script_btn)

        # 5. NFE Execution Section
        nfe_group = QGroupBox("Executar Módulo / Instalador NFE")
        nfe_layout = QVBoxLayout(nfe_group)

        nfe_row = QHBoxLayout()
        self.nfe_path_entry = QLineEdit()
        self.nfe_path_entry.setPlaceholderText("Selecione o executável NFE (ex: NFE.exe ou InstalaNFE.exe)...")
        btn_browse_nfe = QPushButton("Procurar...")
        btn_browse_nfe.setFixedWidth(100)
        btn_browse_nfe.clicked.connect(self.browse_nfe_file)
        nfe_row.addWidget(self.nfe_path_entry, 1)
        nfe_row.addWidget(btn_browse_nfe)
        nfe_layout.addLayout(nfe_row)

        nfe_btn_row = QHBoxLayout()
        self.run_nfe_btn = QPushButton("🚀 Executar NFE como Administrador")
        self.run_nfe_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #585b70;
                color: #a6adc8;
            }
        """)
        self.run_nfe_btn.clicked.connect(self.start_nfe_execution)

        self.kill_nfe_btn = QPushButton("🛑 Encerrar NFE (nfe.exe)")
        self.kill_nfe_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        self.kill_nfe_btn.clicked.connect(self.kill_nfe_process)

        nfe_btn_row.addWidget(self.run_nfe_btn, 2)
        nfe_btn_row.addWidget(self.kill_nfe_btn, 1)
        nfe_layout.addLayout(nfe_btn_row)

        layout.addWidget(nfe_group)


        # 6. Exec Status & Console Log
        self.exec_status_label = QLabel("Status: Pronto.")
        self.exec_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.exec_status_label)

        self.exec_log_box = QTextEdit()
        self.exec_log_box.setReadOnly(True)
        self.exec_log_box.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #181825; color: #cdd6f4; border: 1px solid #45475a;")
        layout.addWidget(self.exec_log_box, 1)

        self.update_db_credentials_display()
        self.auto_detect_execution_files()



    def setup_tab_distribution(self):
        tab = self.frame_distribution
        layout = QHBoxLayout(tab)

        # Left Column: Servers Management
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        lbl_servers = QLabel("Servidores de Distribuição Configurados")
        lbl_servers.setStyleSheet("font-size: 14px; font-weight: bold;")
        left_layout.addWidget(lbl_servers)

        # Add Server Form
        form_group = QGroupBox("Adicionar / Editar Servidor")
        form_layout = QVBoxLayout(form_group)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("IP / Host:"))
        self.srv_ip_entry = QLineEdit()
        self.srv_ip_entry.setPlaceholderText("Ex: 192.168.1.10")
        ip_row.addWidget(self.srv_ip_entry, 1)
        form_layout.addLayout(ip_row)

        share_row = QHBoxLayout()
        share_row.addWidget(QLabel("Compartilhamento:"))
        self.srv_share_entry = QLineEdit()
        self.srv_share_entry.setPlaceholderText("Ex: NBS ou C$")
        share_row.addWidget(self.srv_share_entry, 1)
        form_layout.addLayout(share_row)

        smb_user_row = QHBoxLayout()
        smb_user_row.addWidget(QLabel("Usuário SMB:"))
        self.srv_smb_user_entry = QLineEdit()
        self.srv_smb_user_entry.setPlaceholderText("Deixe vazio para usar usuário atual")
        smb_user_row.addWidget(self.srv_smb_user_entry, 1)
        form_layout.addLayout(smb_user_row)

        smb_pass_row = QHBoxLayout()
        smb_pass_row.addWidget(QLabel("Senha SMB:"))
        self.srv_smb_pass_entry = QLineEdit()
        self.srv_smb_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        smb_pass_row.addWidget(self.srv_smb_pass_entry, 1)
        form_layout.addLayout(smb_pass_row)

        btn_add_srv = QPushButton("+ Adicionar Servidor")
        btn_add_srv.clicked.connect(self.add_server_action)
        form_layout.addWidget(btn_add_srv)

        left_layout.addWidget(form_group)

        # Servers List Widget
        self.servers_list_widget = QListWidget()
        left_layout.addWidget(self.servers_list_widget, 1)

        btn_del_srv = QPushButton("- Remover Servidor Selecionado")
        btn_del_srv.setStyleSheet("background-color: #c0392b; color: white;")
        btn_del_srv.clicked.connect(self.remove_server_action)
        left_layout.addWidget(btn_del_srv)

        # Right Column: Distribution Logs & Action
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.copy_local_var = QCheckBox("Atualizar NBS Local")
        self.copy_local_var.setChecked(True)
        self.copy_servers_var = QCheckBox("Distribuir para os servidores de rede")
        self.copy_servers_var.setChecked(True)

        right_layout.addWidget(self.copy_local_var)
        right_layout.addWidget(self.copy_servers_var)

        self.dist_status_label = QLabel("Status: Aguardando comando...")
        self.dist_status_label.setStyleSheet("font-weight: bold;")
        self.dist_progressbar = QProgressBar()
        self.dist_progressbar.setRange(0, 100)

        self.dist_log_box = QTextEdit()
        self.dist_log_box.setReadOnly(True)
        self.dist_log_box.setStyleSheet("font-family: monospace; font-size: 11px;")

        self.btn_run_dist = QPushButton("Iniciar Distribuição de Arquivos")
        self.btn_run_dist.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_dist.clicked.connect(self.run_copy_distribution)

        right_layout.addWidget(self.dist_status_label)
        right_layout.addWidget(self.dist_progressbar)
        right_layout.addWidget(self.dist_log_box, 1)
        right_layout.addWidget(self.btn_run_dist)

        layout.addWidget(left_widget, 1)
        layout.addWidget(right_widget, 1)

    def setup_tab_utilities(self):
        tab = self.frame_utilities
        layout = QVBoxLayout(tab)

        lbl = QLabel("Ferramentas e Utilitários NBS")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)

        grid_group = QGroupBox("Ações Rápidas")
        grid_layout = QGridLayout(grid_group)

        btn_ext_clean = QPushButton("🧹 Limpeza de Arquivos por Regex / Extensão (NBS)")
        btn_ext_clean.setStyleSheet("padding: 12px; font-weight: bold;")
        btn_ext_clean.clicked.connect(lambda: self.open_extension_cleanup_popup("nbs"))

        CTkToolTip(btn_ext_clean, "Abre a ferramenta de limpeza por extensão de arquivo no diretório NBS.")

        btn_ps_reboot = QPushButton("⚡ Reinício Remoto de Servidor (PowerShell)")
        btn_ps_reboot.setStyleSheet("padding: 12px; font-weight: bold;")
        btn_ps_reboot.clicked.connect(lambda: self.open_powershell_restart_popup("nbs"))
        CTkToolTip(btn_ps_reboot, "Envia o comando Restart-Computer via PowerShell para reinício de servidores remotos.")

        btn_open_nbs = QPushButton("📂 Abrir Pasta C:\\NBS")
        btn_open_nbs.setStyleSheet("padding: 12px;")
        btn_open_nbs.clicked.connect(lambda: self.open_folder_explorer("nbs"))

        btn_open_up = QPushButton("📂 Abrir Pasta C:\\Atualizacao")
        btn_open_up.setStyleSheet("padding: 12px;")
        btn_open_up.clicked.connect(lambda: self.open_folder_explorer("atualizacao"))

        btn_taskschd = QPushButton("⏰ Abrir Agendador de Tarefas do Windows")
        btn_taskschd.setStyleSheet("padding: 12px;")
        btn_taskschd.clicked.connect(self.open_taskschd)

        grid_layout.addWidget(btn_ext_clean, 0, 0)
        grid_layout.addWidget(btn_ps_reboot, 0, 1)
        grid_layout.addWidget(btn_open_nbs, 1, 0)
        grid_layout.addWidget(btn_open_up, 1, 1)
        grid_layout.addWidget(btn_taskschd, 2, 0, 1, 2)

        layout.addWidget(grid_group)
        layout.addStretch(1)

    def setup_tab_crmweb(self):
        tab = self.frame_crmweb
        layout = QVBoxLayout(tab)

        lbl = QLabel("Gerenciamento e Execução dos Módulos CRM")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)

        # --- PARTE 1: CRM GOLD ---
        gold_group = QGroupBox("1. CRM Gold (Instalador / Atualizador)")
        gold_layout = QVBoxLayout(gold_group)

        gold_row = QHBoxLayout()
        gold_row.addWidget(QLabel("Comando / Atalho CRM Gold:"))
        self.crm_gold_cmd_entry = QLineEdit("C:\\Java\\Update_BSC_CRMGold\\WEUpdate.exe -suporte")
        btn_run_gold = QPushButton("🚀 Executar CRM Gold (-suporte)")
        btn_run_gold.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_run_gold.clicked.connect(self.run_crm_gold)
        gold_row.addWidget(self.crm_gold_cmd_entry, 1)
        gold_row.addWidget(btn_run_gold)
        gold_layout.addLayout(gold_row)
        layout.addWidget(gold_group)

        # --- PARTE 2: CRM PARTS / SERVICE ---
        parts_group = QGroupBox("2. CRM Parts / Service")
        parts_layout = QVBoxLayout(parts_group)

        parts_row = QHBoxLayout()
        parts_row.addWidget(QLabel("Comando / Atalho CRM Parts:"))
        self.crm_parts_cmd_entry = QLineEdit("C:\\Java\\JManagerClient\\JManagerClient.exe -suporte -disablehash")
        btn_run_parts = QPushButton("🚀 Executar CRM Parts / Service")
        btn_run_parts.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 6px;")
        btn_run_parts.clicked.connect(self.run_crm_parts)
        parts_row.addWidget(self.crm_parts_cmd_entry, 1)
        parts_row.addWidget(btn_run_parts)
        parts_layout.addLayout(parts_row)
        layout.addWidget(parts_group)

        # --- PARTE 3: SERVIÇO PAYARA (domain1) ---
        payara_group = QGroupBox("3. Serviço Payara (domain1)")
        payara_layout = QVBoxLayout(payara_group)

        p_row1 = QHBoxLayout()
        p_row1.addWidget(QLabel("Nome do Serviço / Domínio Payara:"))
        self.crm_payara_entry = QLineEdit("domain1")
        self.lbl_payara_status = QLabel("DESCONHECIDO")
        self.lbl_payara_status.setFixedWidth(120)
        self.lbl_payara_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_payara_status.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
        p_row1.addWidget(self.crm_payara_entry, 1)
        p_row1.addWidget(self.lbl_payara_status)
        payara_layout.addLayout(p_row1)

        p_btn_row = QHBoxLayout()
        btn_start_payara = QPushButton("▶ Iniciar Serviço Payara")
        btn_start_payara.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_start_payara.clicked.connect(self.start_payara_service)

        btn_stop_payara = QPushButton("⏹ Parar Serviço Payara")
        btn_stop_payara.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 6px;")
        btn_stop_payara.clicked.connect(self.stop_payara_service)

        btn_check_payara = QPushButton("🔄 Verificar Status")
        btn_check_payara.setStyleSheet("padding: 6px;")
        btn_check_payara.clicked.connect(self.check_payara_status)

        p_btn_row.addWidget(btn_start_payara)
        p_btn_row.addWidget(btn_stop_payara)
        p_btn_row.addWidget(btn_check_payara)
        payara_layout.addLayout(p_btn_row)

        layout.addWidget(payara_group)

        # Console Log
        self.crm_log_box = QTextEdit()
        self.crm_log_box.setReadOnly(True)
        self.crm_log_box.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.crm_log_box, 1)



    def setup_tab_settings(self):
        tab = self.frame_settings
        layout = QVBoxLayout(tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        # FTP Section
        ftp_group = QGroupBox("Configurações de Servidores FTP")
        ftp_layout = QVBoxLayout(ftp_group)

        ftp_layout.addWidget(QLabel("FTP Módulos Oficiais:"))
        self.ftp_modules_entry = QLineEdit()
        ftp_layout.addWidget(self.ftp_modules_entry)

        ftp_layout.addWidget(QLabel("FTP Scripts:"))
        self.ftp_scripts_entry = QLineEdit()
        ftp_layout.addWidget(self.ftp_scripts_entry)

        ftp_layout.addWidget(QLabel("FTP NFE:"))
        self.ftp_nfe_entry = QLineEdit()
        ftp_layout.addWidget(self.ftp_nfe_entry)

        ftp_layout.addWidget(QLabel("FTP Interfaces de Marcas:"))
        self.ftp_interfaces_entry = QLineEdit()
        ftp_layout.addWidget(self.ftp_interfaces_entry)

        ftp_layout.addWidget(QLabel("FTP DLLs:"))
        self.ftp_dll_entry = QLineEdit()
        ftp_layout.addWidget(self.ftp_dll_entry)

        auth_row = QHBoxLayout()
        auth_row.addWidget(QLabel("Usuário FTP:"))
        self.ftp_user_entry = QLineEdit()
        auth_row.addWidget(self.ftp_user_entry, 1)

        auth_row.addWidget(QLabel("Senha FTP:"))
        self.ftp_pass_entry = QLineEdit()
        self.ftp_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        auth_row.addWidget(self.ftp_pass_entry, 1)

        self.ftp_pass_btn = QPushButton("👁")
        self.ftp_pass_btn.setFixedWidth(40)
        self.ftp_pass_btn.clicked.connect(self.toggle_ftp_password)
        auth_row.addWidget(self.ftp_pass_btn)
        ftp_layout.addLayout(auth_row)

        scroll_layout.addWidget(ftp_group)

        # Paths Section
        paths_group = QGroupBox("Caminhos Locais no Sistema")
        paths_layout = QVBoxLayout(paths_group)

        up_row = QHBoxLayout()
        up_row.addWidget(QLabel("Pasta C:\\Atualizacao (Local):"))
        self.atualiza_path_entry = QLineEdit()
        btn_browse_up = QPushButton("...")
        btn_browse_up.setFixedWidth(40)
        btn_browse_up.clicked.connect(lambda: self.browse_directory(self.atualiza_path_entry))
        up_row.addWidget(self.atualiza_path_entry, 1)
        up_row.addWidget(btn_browse_up)
        paths_layout.addLayout(up_row)

        nbs_row = QHBoxLayout()
        nbs_row.addWidget(QLabel("Pasta C:\\NBS (Local):"))
        self.nbs_path_entry = QLineEdit()
        btn_browse_nbs = QPushButton("...")
        btn_browse_nbs.setFixedWidth(40)
        btn_browse_nbs.clicked.connect(lambda: self.browse_directory(self.nbs_path_entry))
        nbs_row.addWidget(self.nbs_path_entry, 1)
        nbs_row.addWidget(btn_browse_nbs)
        paths_layout.addLayout(nbs_row)

        scroll_layout.addWidget(paths_group)

        # DB Section
        db_group = QGroupBox("Banco de Dados Oracle")
        db_layout = QGridLayout(db_group)

        db_layout.addWidget(QLabel("Usuário Banco:"), 0, 0)
        self.db_user_entry = QLineEdit()
        db_layout.addWidget(self.db_user_entry, 0, 1)

        db_layout.addWidget(QLabel("Senha Banco:"), 0, 2)
        self.db_pass_entry = QLineEdit()
        self.db_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        db_layout.addWidget(self.db_pass_entry, 0, 3)

        db_layout.addWidget(QLabel("Schema / Host:"), 1, 0)
        self.db_schema_entry = QLineEdit()
        db_layout.addWidget(self.db_schema_entry, 1, 1)

        db_layout.addWidget(QLabel("Service Name:"), 1, 2)
        self.db_name_entry = QLineEdit()
        db_layout.addWidget(self.db_name_entry, 1, 3)

        scroll_layout.addWidget(db_group)

        # Appearance Section
        app_group = QGroupBox("Aparência Visual")
        app_layout = QHBoxLayout(app_group)
        app_layout.addWidget(QLabel("Modo do Tema:"))
        self.settings_appearance_menu = QComboBox()
        self.settings_appearance_menu.addItems(["Dark", "Light", "System"])
        app_layout.addWidget(self.settings_appearance_menu, 1)
        scroll_layout.addWidget(app_group)

        layout.addWidget(scroll, 1)

        btn_save = QPushButton("Salvar Configurações")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 12px; font-size: 14px;")
        btn_save.clicked.connect(self.save_settings_manually)
        layout.addWidget(btn_save)

    def setup_tab_about(self):
        tab = self.frame_about
        layout = QVBoxLayout(tab)

        # Info Group
        info_group = QGroupBox("Informações do Desenvolvedor e Versão")
        info_layout = QVBoxLayout(info_group)
        details_text = (
            "Desenvolvedor: Robson Santos\n"
            "Contato: robsonshk@gmail.com\n"
            "Versão do Programa: 2.0.0\n"
            "Finalidade: Facilitar a automação e controle do processo de atualizações de sistemas NBS."
        )
        lbl_info = QLabel(details_text)
        lbl_info.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(lbl_info)
        layout.addWidget(info_group)

        # License Info Group
        lic_group = QGroupBox("🔒 Status do Licenciamento")
        lic_layout = QVBoxLayout(lic_group)

        lm = LicenseManager(app_name="AtualizadorSistemas")
        lic = lm.load_license()

        status_str = "🟢 Licença Ativa e Válida" if lic.get("is_valid") else "🔴 Licença Inativa / Não Validada"
        empresa_str = lic.get("company_name", "Não informada")
        validade_str = lic.get("valid_until", "Indefinida")
        hwid_str = get_hwid()

        self.lbl_lic_status = QLabel(f"Status: {status_str}")
        self.lbl_lic_status.setStyleSheet("font-weight: bold;")
        self.lbl_lic_company = QLabel(f"Empresa: {empresa_str}")
        self.lbl_lic_validity = QLabel(f"Validade: {validade_str}")
        self.lbl_lic_hwid = QLabel(f"Hardware ID (HWID): {hwid_str}")
        self.lbl_lic_hwid.setStyleSheet("font-family: monospace; font-size: 10px; color: #aaa;")

        btn_manage_lic = QPushButton("Gerenciar / Reativar Licença")
        btn_manage_lic.setStyleSheet("padding: 6px; font-weight: bold;")
        btn_manage_lic.clicked.connect(self.open_license_manager)

        lic_layout.addWidget(self.lbl_lic_status)
        lic_layout.addWidget(self.lbl_lic_company)
        lic_layout.addWidget(self.lbl_lic_validity)
        lic_layout.addWidget(self.lbl_lic_hwid)
        lic_layout.addWidget(btn_manage_lic)

        layout.addWidget(lic_group)

        # Changelog Group
        change_group = QGroupBox("Histórico de Alterações (Changelog)")
        change_layout = QVBoxLayout(change_group)
        txt_change = QTextEdit()
        txt_change.setReadOnly(True)
        txt_change.setText(CHANGELOG_NBS)
        change_layout.addWidget(txt_change)
        layout.addWidget(change_group, 1)

    def setup_tab_nbs_notes(self):
        tab = self.frame_nbs_notes
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        lbl_title = QLabel("📝 Observações e Anotações da Máquina / Cliente (NBS)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        lbl_subtitle = QLabel("Espaço livre para salvar anotações pertinentes à configuração desta máquina, IP de banco, particularidades, etc.")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)

        self.nbs_notes_box = QTextEdit()
        self.nbs_notes_box.setReadOnly(False)
        self.nbs_notes_box.setPlaceholderText("Digite aqui suas observações sobre esta máquina ou cliente...")
        self.nbs_notes_box.setStyleSheet("font-family: sans-serif; font-size: 13px; background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; padding: 8px;")

        initial_notes = getattr(self, "app_config", {}).get("nbs_notes", "")
        if initial_notes:
            self.nbs_notes_box.setPlainText(initial_notes)

        layout.addWidget(self.nbs_notes_box, 1)

        footer_layout = QHBoxLayout()
        self.nbs_notes_status_lbl = QLabel("")
        self.nbs_notes_status_lbl.setStyleSheet("font-size: 12px; color: #a6e3a1; font-weight: bold;")
        footer_layout.addWidget(self.nbs_notes_status_lbl, 1)

        btn_save = QPushButton("💾 Salvar Observações")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        btn_save.clicked.connect(self.save_nbs_notes)
        footer_layout.addWidget(btn_save)

        layout.addLayout(footer_layout)

    def save_nbs_notes(self):
        if hasattr(self, "nbs_notes_box"):
            notes_text = self.nbs_notes_box.toPlainText()
            self.app_config["nbs_notes"] = notes_text
            if config.save_config(self.app_config):
                now_str = datetime.now().strftime("%H:%M:%S")
                if hasattr(self, "nbs_notes_status_lbl"):
                    self.nbs_notes_status_lbl.setText(f"✓ Observações salvas às {now_str}")
                QMessageBox.information(self, "Sucesso", "Observações salvas com sucesso!")
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível salvar as observações no arquivo de configuração.")


    def open_license_manager(self):
        lm = LicenseManager(app_name="AtualizadorSistemas")
        dialog = LicenseActivationDialog(lm, parent=self)
        dialog.exec()
        # Refresh displays
        lic = lm.load_license()
        status_str = "🟢 Licença Ativa e Válida" if lic.get("is_valid") else "🔴 Licença Inativa / Não Validada"
        self.lbl_lic_status.setText(f"Status: {status_str}")
        self.lbl_lic_company.setText(f"Empresa: {lic.get('company_name', 'Não informada')}")
        self.lbl_lic_validity.setText(f"Validade: {lic.get('valid_until', 'Indefinida')}")

    def toggle_ftp_password(self):
        if self.ftp_pass_entry.echoMode() == QLineEdit.EchoMode.Password:
            self.ftp_pass_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.ftp_pass_btn.setText("🔒")
        else:
            self.ftp_pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.ftp_pass_btn.setText("👁")

    def auto_detect_cutoff_date(self):
        c = self.app_config
        p_up = c.get("atualizacao_path_win", "C:\\Atualizacao") if self.os_type == "Windows" else c.get("atualizacao_path_linux", "./Atualizacao")
        last_date = utils.get_last_update_date(p_up)
        if last_date:
            date_str = last_date.strftime("%d/%m/%Y")
            self.cutoff_date_entry.setText(date_str)
            self.log_dl(f"Última data de atualização detectada a partir de {p_up}: {date_str}")
        else:
            self.cutoff_date_entry.setText("")
            self.log_dl(f"Nenhuma pasta anterior ddMMyyyy encontrada em {p_up}. Todos os arquivos serão baixados.")

    def on_toggle_interfaces(self, state=None):
        is_checked = self.download_interfaces_var.isChecked()
        self.brands_group.setVisible(is_checked)
        if is_checked:
            self.fetch_brands()

    def on_toggle_initial_installation(self, state=None):
        is_init = self.initial_installation_var.isChecked()
        self.cutoff_date_entry.setEnabled(not is_init)
        self.recalc_btn.setEnabled(not is_init)

    def log_debug(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [DEBUG] {msg}"
        print(formatted, flush=True)

        try:
            log_dir = os.path.join(os.environ.get("APPDATA", "."), "MonitorNBS", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

    def append_log_debug_ui(self, formatted):
        # Muted: Debug logs are saved to debug.log file and stdout only, keeping UI screens clean
        pass


    def fetch_brands(self):
        # Clear existing brand checkboxes
        while self.brands_layout.count():
            item = self.brands_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.brand_checkboxes.clear()

        c = self.app_config
        ftp_url = c.get("ftp_interfaces_url", "")
        user = c.get("ftp_user", "")
        pwd = c.get("ftp_pass", "")

        if not ftp_url:
            if hasattr(self, 'brands_status_lbl'):
                self.brands_status_lbl.setText("⚠️ URL do FTP de Interfaces não configurada em Configurações.")
                self.brands_status_lbl.show()
            return

        if hasattr(self, 'brands_status_lbl'):
            self.brands_status_lbl.setText("🔄 Conectando ao FTP e listando pastas de marcas...")
            self.brands_status_lbl.show()

        host, port, remote_path = ftp_client.parse_ftp_url(ftp_url)
        self.log_debug(f"Iniciando busca de marcas. FTP Host: '{host}', Port: {port}, Path: '{remote_path}', User: '{user}'")

        def _fetch():
            try:
                self.log_debug(f"Conectando ao FTP '{host}:{port}'...")
                client = ftp_client.FTPClient(host, port=port, user=user, password=pwd)
                client.connect()
                self.log_debug(f"Conexão FTP estabelecida com sucesso. Listando subdiretórios em '{remote_path}'...")
                dirs = client.list_subdirs(remote_path)
                client.disconnect()
                self.log_debug(f"Busca finalizada. {len(dirs)} subdiretórios encontrados no FTP: {dirs}")

                if hasattr(self, 'brands_fetched_signal'):
                    self.brands_fetched_signal.emit(dirs)
                else:
                    QTimer.singleShot(0, lambda: self.on_brands_fetched_success(dirs))
            except Exception as e:
                self.log_debug(f"ERRO ao listar marcas no FTP: {e}")
                if hasattr(self, 'brands_failed_signal'):
                    self.brands_failed_signal.emit(str(e))
                else:
                    QTimer.singleShot(0, lambda: self.on_brands_fetched_failed(str(e)))

        threading.Thread(target=_fetch, daemon=True).start()

    def on_brands_fetched_success(self, dirs):
        if hasattr(self, 'brands_status_lbl'):
            self.brands_status_lbl.hide()

        # Clear existing layout items
        while self.brands_layout.count():
            item = self.brands_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.brand_checkboxes.clear()

        saved_selected = self.app_config.get("selected_interfaces", [])

        for brand in sorted(dirs, key=lambda s: str(s).upper()):
            chk = QCheckBox(brand)
            chk.setStyleSheet("QCheckBox { color: #cdd6f4; font-size: 13px; padding: 2px 4px; } QCheckBox::indicator { width: 16px; height: 16px; }")
            if saved_selected:
                chk.setChecked(brand in saved_selected)
            else:
                chk.setChecked(False)  # Default desmarcado

            chk.stateChanged.connect(self.save_ui_to_config)
            self.brands_layout.addWidget(chk)
            self.brand_checkboxes[brand] = chk
            chk.show()


        # Force scroll container layout update in PySide6
        self.brands_content.adjustSize()
        self.brands_scroll.setWidget(self.brands_content)
        self.brands_content.show()
        self.brands_scroll.show()
        self.brands_group.update()

        if hasattr(self, 'brand_search_entry'):
            self.filter_brands(self.brand_search_entry.text())

        self.log_debug(f"[UI REFRESH] {len(dirs)} marcas exibidas no filtro da tela.")

    def on_brands_fetched_failed(self, error_msg):
        if hasattr(self, 'brands_status_lbl'):
            self.brands_status_lbl.setText(f"❌ Erro ao listar marcas do FTP: {error_msg}")
            self.brands_status_lbl.show()
        self.log_debug(f"[UI ERROR] Falha ao carregar marcas: {error_msg}")


        threading.Thread(target=_fetch, daemon=True).start()


    def filter_brands(self, text=""):
        query = text.strip().lower()
        for brand_name, chk in self.brand_checkboxes.items():
            if not query or query in brand_name.lower():
                chk.show()
            else:
                chk.hide()

    def set_all_brands_checked(self, checked=True):
        for chk in self.brand_checkboxes.values():
            if chk.isVisible():
                chk.setChecked(checked)
        self.save_ui_to_config()


    def auto_detect_execution_files(self):
        c = getattr(self, "app_config", {})
        atualiza_path = c.get("atualizacao_path_win" if getattr(self, "os_type", "Windows") == "Windows" else "atualizacao_path_linux", "C:\\Atualizacao")

        script_file = utils.find_latest_nbs_script(atualiza_path)
        if script_file and hasattr(self, 'script_path_entry'):
            self.script_path_entry.setText(os.path.normpath(script_file))

        nfe_file = utils.find_latest_nfe_file(atualiza_path)
        if nfe_file and hasattr(self, 'nfe_path_entry'):
            self.nfe_path_entry.setText(os.path.normpath(nfe_file))

    def browse_script_file(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo de Script NBS", "", "Arquivos Executáveis (*.exe);;Todos os Arquivos (*.*)")
        if selected:
            self.script_path_entry.setText(os.path.normpath(selected))

    def browse_nfe_file(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo NFE", "", "Arquivos Executáveis (*.exe);;Todos os Arquivos (*.*)")
        if selected:
            self.nfe_path_entry.setText(os.path.normpath(selected))

    def start_nfe_execution(self):
        filepath = self.nfe_path_entry.text().strip()
        if not filepath:
            QMessageBox.critical(self, "Erro", "Selecione o executável NFE para executar.")
            return

        if not os.path.exists(filepath):
            QMessageBox.critical(self, "Erro", f"O arquivo NFE especificado não existe:\n{filepath}")
            return

        self.run_nfe_btn.setEnabled(False)
        self.exec_status_label.setText("Status: Executando NFE...")
        self.exec_log_box.clear()
        self.log_exec(f"Iniciando executável NFE: {os.path.basename(filepath)}")

        def _nfe_thread():
            log = self.log_exec
            status = self.status_exec

            try:
                if self.os_type != "Windows":
                    status("Executando NFE (Simulação)...")
                    log(f"Iniciando NFE principal (Simulação): {os.path.basename(filepath)}")
                    time.sleep(2)
                    log("[Linux SIMULADO] Instalador NFE finalizado.")
                    log("[Linux SIMULADO] Validador instaladoNFE.exe iniciado automaticamente.")
                    time.sleep(2)
                    log("[Linux SIMULADO] Validador instaladoNFE.exe finalizado.")
                    status("Concluído.")
                    if hasattr(self, "exec_finished_signal"):
                        self.exec_finished_signal.emit(True, "Instalador NFE e processo instaladoNFE.exe executados com sucesso!")
                    return

                success = utils.execute_script_as_admin(filepath, log)
                if not success:
                    status("Erro NFE.")
                    if hasattr(self, "exec_finished_signal"):
                        self.exec_finished_signal.emit(False, "O instalador NFE reportou erro ou foi cancelado pelo usuário.")
                    return

                log("Instalador NFE descompactado. Monitorando inicialização do processo instaladoNFE.exe...")
                status("Aguardando instaladoNFE.exe...")

                is_running = False
                for i in range(10):
                    time.sleep(1)
                    if self.is_process_running("instaladoNFE.exe") or self.is_process_running("instaladorNFE.exe"):
                        is_running = True
                        break
                    if i % 3 == 0:
                        log("Verificando se instaladoNFE.exe foi iniciado...")

                if is_running:
                    log("Processo instaladoNFE.exe detectado em execução. Aguardando conclusão do processo...")
                    status("Executando instaladoNFE.exe...")
                    while self.is_process_running("instaladoNFE.exe") or self.is_process_running("instaladorNFE.exe"):
                        time.sleep(2)
                    log("Processo instaladoNFE.exe finalizado com sucesso.")
                    status("Concluído.")
                    if hasattr(self, "exec_finished_signal"):
                        self.exec_finished_signal.emit(True, "Instalador NFE e processo instaladoNFE.exe executados e finalizados com sucesso!")
                else:
                    log("Executável Instalador NFE finalizado.")
                    status("Concluído.")
                    if hasattr(self, "exec_finished_signal"):
                        self.exec_finished_signal.emit(True, "Instalador NFE executado com sucesso!")
            except Exception as e:
                log(f"ERRO ao executar NFE: {e}")
                status(f"Erro NFE: {e}")
                if hasattr(self, "exec_finished_signal"):
                    self.exec_finished_signal.emit(False, f"Erro ao executar NFE: {e}")
            finally:
                QTimer.singleShot(0, lambda: self.run_nfe_btn.setEnabled(True))

        threading.Thread(target=_nfe_thread, daemon=True).start()

    def kill_nfe_process(self):
        try:
            import subprocess
            if self.os_type == "Windows":
                res = subprocess.run(["taskkill", "/F", "/IM", "nfe.exe"], capture_output=True, text=True, creationflags=0x08000000)
                out = (res.stdout + res.stderr).lower()
                if "não foi encontrado" in out or "not found" in out or "no process" in out:
                    QMessageBox.information(self, "Encerrar NFE", "O processo nfe.exe não está em execução no momento.")
                else:
                    QMessageBox.information(self, "Encerrar NFE", "O processo nfe.exe foi encerrado com sucesso!")
            else:
                subprocess.run(["pkill", "-f", "nfe.exe"], capture_output=True, text=True)
                QMessageBox.information(self, "Encerrar NFE", "Sinal de encerramento enviado para nfe.exe.")
            self.log_exec("Comando de encerramento do processo nfe.exe executado.")
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Erro ao encerrar nfe.exe: {e}")

    def toggle_db_credentials(self):
        self.db_credentials_visible = not getattr(self, "db_credentials_visible", False)
        self.update_db_credentials_display()

    def update_db_credentials_display(self):
        c = getattr(self, "app_config", {})
        u = c.get("db_user", "Não Configurado")
        s = c.get("db_schema", "Não Configurado")
        n = c.get("db_name", "Não Configurado")
        p = c.get("db_pass", c.get("db_password", "Não Configurado"))

        if hasattr(self, "db_user_lbl"):
            if getattr(self, "db_credentials_visible", False):
                self.db_user_lbl.setText(f"Usuário: {u}")
                self.db_schema_lbl.setText(f"Schema/Host: {s}")
                self.db_name_lbl.setText(f"Service Name: {n}")
                self.db_pass_lbl.setText(f"Senha: {p}")
                self.db_toggle_btn.setText("Ocultar Credenciais")
            else:
                self.db_user_lbl.setText(f"Usuário: {len(u) * '•' if u else '••••••••'}")
                self.db_schema_lbl.setText(f"Schema/Host: {len(s) * '•' if s else '••••••••'}")
                self.db_name_lbl.setText(f"Service Name: {len(n) * '•' if n else '••••••••'}")
                self.db_pass_lbl.setText(f"Senha: {len(p) * '•' if p else '••••••••'}")
                self.db_toggle_btn.setText("Exibir Credenciais")

    def start_script_execution(self):
        filepath = self.script_path_entry.text().strip()
        if not filepath:
            QMessageBox.critical(self, "Erro", "Selecione o arquivo de script NBS Scripts para executar.")
            return

        if not os.path.exists(filepath):
            QMessageBox.critical(self, "Erro", f"O arquivo de script especificado não existe:\n{filepath}")
            return

        self.run_script_btn.setEnabled(False)
        self.exec_status_label.setText("Status: Preparando execução...")
        self.exec_log_box.clear()

        threading.Thread(target=self._script_execution_thread, args=(filepath,), daemon=True).start()

    def is_process_running(self, name):
        try:
            import subprocess
            if self.os_type == "Windows":
                out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}"], capture_output=True, text=True, creationflags=0x08000000)
                return name.lower() in out.stdout.lower()
            else:
                out = subprocess.run(["ps", "ax"], capture_output=True, text=True)
                return name.lower() in out.stdout.lower()
        except Exception:
            return False

    def log_exec(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        print(formatted, flush=True)
        if hasattr(self, "exec_log_signal"):
            self.exec_log_signal.emit(formatted)
        elif hasattr(self, "exec_log_box"):
            self.log_exec_ui(formatted)

    def log_exec_ui(self, formatted):
        if hasattr(self, "exec_log_box"):
            self.exec_log_box.append(formatted)
            self.exec_log_box.verticalScrollBar().setValue(self.exec_log_box.verticalScrollBar().maximum())

    def status_exec(self, text):
        msg = f"Status: {text}"
        if hasattr(self, "exec_status_signal"):
            self.exec_status_signal.emit(msg)
        elif hasattr(self, "exec_status_label"):
            self.status_exec_ui(msg)

    def status_exec_ui(self, msg):
        if hasattr(self, "exec_status_label"):
            self.exec_status_label.setText(msg)

    def on_script_execution_finished(self, success: bool, message: str):
        self.run_script_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Sucesso", message)
        else:
            QMessageBox.warning(self, "Execução Finalizada", message)

    def _script_execution_thread(self, filepath):
        log = self.log_exec
        status = self.status_exec

        try:
            if self.os_type != "Windows":
                status("Executando Script (Simulação)...")
                log(f"Iniciando script principal (Simulação): {os.path.basename(filepath)}")
                time.sleep(2)
                log("[Linux SIMULADO] Script principal finalizado.")
                log("[Linux SIMULADO] Validador NBSScriptsRun.exe iniciado automaticamente.")
                time.sleep(2)
                log("[Linux SIMULADO] Validador NBSScriptsRun.exe finalizado.")
                status("Concluído.")
                if hasattr(self, "exec_finished_signal"):
                    self.exec_finished_signal.emit(True, "Script de banco e validador NBSScriptsRun.exe executados com sucesso!")
                return

            status("Executando Script...")
            log(f"Iniciando script de banco principal: {os.path.basename(filepath)}")

            success1 = utils.execute_script_as_admin(filepath, log)
            if not success1:
                status("Erro.")
                if hasattr(self, "exec_finished_signal"):
                    self.exec_finished_signal.emit(False, "O script principal reportou erro ou foi cancelado pelo usuário.")
                return

            log("Script principal finalizado. Monitorando inicialização do validador NBSScriptsRun.exe...")
            status("Aguardando validador...")

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
                while self.is_process_running("NBSScriptsRun.exe"):
                    time.sleep(2)
                log("Validador NBSScriptsRun.exe finalizado com sucesso.")
                status("Concluído.")

                if hasattr(self, "exec_finished_signal"):
                    self.exec_finished_signal.emit(True, "Script de banco e validador NBSScriptsRun.exe executados e finalizados com sucesso!")
            else:
                log("Alerta: O validador NBSScriptsRun.exe não foi iniciado automaticamente.")
                status("Concluído (Manual).")

                if hasattr(self, "exec_finished_signal"):
                    self.exec_finished_signal.emit(True, "Script de banco concluído com sucesso!")

        except Exception as e:
            log(f"ERRO durante a execução do script: {e}")
            status(f"Erro: {e}")
            if hasattr(self, "exec_finished_signal"):
                self.exec_finished_signal.emit(False, f"Erro ao executar script: {e}")





    def browse_directory(self, entry_widget):
        selected = QFileDialog.getExistingDirectory(self, "Selecionar pasta")
        if selected:
            entry_widget.setText(selected)
            self.save_ui_to_config()

    def save_settings_manually(self):
        self.save_ui_to_config()
        QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")

    def add_server_action(self):
        ip = self.srv_ip_entry.text().strip()
        share = self.srv_share_entry.text().strip()
        user = self.srv_smb_user_entry.text().strip()
        pwd = self.srv_smb_pass_entry.text().strip()

        if not ip:
            QMessageBox.warning(self, "Aviso", "Informe o IP ou Hostname do servidor.")
            return

        srv_obj = {"ip": ip, "share": share, "user": user, "pass": pwd}
        c = self.app_config
        servers = c.get("servers", [])
        servers.append(srv_obj)
        c["servers"] = servers
        config.save_config(c)

        self.refresh_servers_list_ui()
        self.srv_ip_entry.clear()
        self.srv_share_entry.clear()
        self.srv_smb_user_entry.clear()
        self.srv_smb_pass_entry.clear()

    def remove_server_action(self):
        curr_item = self.servers_list_widget.currentItem()
        if not curr_item:
            return
        idx = self.servers_list_widget.row(curr_item)
        c = self.app_config
        servers = c.get("servers", [])
        if 0 <= idx < len(servers):
            servers.pop(idx)
            c["servers"] = servers
            config.save_config(c)
            self.refresh_servers_list_ui()

    def refresh_servers_list_ui(self):
        self.servers_list_widget.clear()
        c = self.app_config
        servers = c.get("servers", [])
        for srv in servers:
            if isinstance(srv, dict):
                ip = srv.get("ip", "")
                share = srv.get("share", "")
                user = srv.get("user", "")
                disp = f"{ip}\\{share}" if share else ip
                if user:
                    disp += f" (user: {user})"
            else:
                disp = str(srv)
            self.servers_list_widget.addItem(disp)

    # ----------------- NBS THREAD LOGIC & DOWNLOAD -----------------
    def set_download_ui_active_state(self, running: bool):
        self.btn_run_download.setEnabled(not running)
        self.btn_pause_download.setEnabled(running)
        self.btn_cancel_download.setEnabled(running)

        if hasattr(self, "nbs_nav_buttons"):
            for btn in self.nbs_nav_buttons:
                btn.setEnabled(not running)
        if hasattr(self, "nav_btn_back_to_selection"):
            self.nav_btn_back_to_selection.setEnabled(not running)

        if hasattr(self, "cutoff_date_entry"):
            self.cutoff_date_entry.setEnabled(not running)
        if hasattr(self, "recalc_btn"):
            self.recalc_btn.setEnabled(not running)
        if hasattr(self, "download_nbs_var"):
            self.download_nbs_var.setEnabled(not running)
        if hasattr(self, "download_scripts_var"):
            self.download_scripts_var.setEnabled(not running)
        if hasattr(self, "download_interfaces_var"):
            self.download_interfaces_var.setEnabled(not running)
        if hasattr(self, "download_nfe_var"):
            self.download_nfe_var.setEnabled(not running)
        if hasattr(self, "initial_installation_var"):
            self.initial_installation_var.setEnabled(not running)
        if hasattr(self, "compress_backup_var"):
            self.compress_backup_var.setEnabled(not running)
        if hasattr(self, "delete_backup_after_compress_var"):
            self.delete_backup_after_compress_var.setEnabled(not running)
        if hasattr(self, "debug_mode_var"):
            self.debug_mode_var.setEnabled(not running)
        if hasattr(self, "brand_search_entry"):
            self.brand_search_entry.setEnabled(not running)

        if hasattr(self, "brand_checkboxes"):
            for chk in self.brand_checkboxes.values():
                chk.setEnabled(not running)

    def run_download_process(self):
        self.save_ui_to_config()
        self.set_download_ui_active_state(running=True)

        self.dl_log_box.clear()
        self.dl_progressbar.setValue(0)
        self.dl_status_label.setText("Iniciando processo...")

        self.is_paused = False
        self.is_cancelled = False

        threading.Thread(target=self._download_process_thread, daemon=True).start()

    def pause_download_process(self):
        self.is_paused = not getattr(self, "is_paused", False)
        txt = "Continuar" if self.is_paused else "Pausar"
        self.btn_pause_download.setText(txt)
        if self.is_paused:
            self.log_dl("Processo pausado pelo usuário.")
        else:
            self.log_dl("Processo retomado.")

    def cancel_download_process(self):
        self.is_cancelled = True
        self.is_paused = False
        self.log_dl("Cancelamento solicitado pelo usuário. Finalizando...")

    def log_dl(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        print(formatted, flush=True)
        if hasattr(self, "dl_log_signal"):
            self.dl_log_signal.emit(formatted)
        elif hasattr(self, "dl_log_box"):
            self.log_dl_ui(formatted)

    def log_dl_ui(self, formatted):
        if hasattr(self, "dl_log_box"):
            self.dl_log_box.append(formatted)
            self.dl_log_box.verticalScrollBar().setValue(self.dl_log_box.verticalScrollBar().maximum())

    def status_dl(self, msg):
        if hasattr(self, "dl_status_signal"):
            self.dl_status_signal.emit(msg)
        elif hasattr(self, "dl_status_label"):
            self.status_dl_ui(msg)

    def status_dl_ui(self, msg):
        if hasattr(self, "dl_status_label"):
            self.dl_status_label.setText(msg)

    def progress_dl(self, val_pct):
        val_int = int(val_pct * 100) if isinstance(val_pct, float) else int(val_pct)
        if hasattr(self, "dl_progress_signal"):
            self.dl_progress_signal.emit(val_int)
        elif hasattr(self, "dl_progressbar"):
            self.progress_dl_ui(val_int)

    def progress_dl_ui(self, val_int):
        if hasattr(self, "dl_progressbar"):
            self.dl_progressbar.setValue(val_int)

    def on_download_process_finished(self, success: bool, message: str):
        self.set_download_ui_active_state(running=False)
        self.btn_pause_download.setText("Pausar")
        self.is_paused = False
        self.is_cancelled = False
        if success:
            self.status_dl("Processo finalizado com sucesso!")
            self.progress_dl(1.0)
        else:
            self.status_dl(f"Status: {message}")


    def _download_process_thread(self):
        log = self.log_dl
        status = self.status_dl
        progress = self.progress_dl

        def check_pause_and_cancel():
            while getattr(self, "is_paused", False):
                time.sleep(0.1)
                if getattr(self, "is_cancelled", False):
                    raise Exception("Processo cancelado pelo usuário.")
            if getattr(self, "is_cancelled", False):
                raise Exception("Processo cancelado pelo usuário.")

        def download_with_control(client_inst, r_file, l_file, size):
            check_pause_and_cancel()

            if os.path.exists(l_file):
                local_size = os.path.getsize(l_file)
                if local_size == size:
                    remote_md5 = client_inst.get_file_md5(r_file)
                    if remote_md5:
                        local_md5 = utils.calculate_local_md5(l_file)
                        if local_md5 == remote_md5:
                            log(f"Arquivo {os.path.basename(l_file)} já baixado (hash OK). Pulando.")
                            progress(1.0)
                            return
                        else:
                            log(f"Arquivo {os.path.basename(l_file)} tem tamanho igual mas hash diferente. Baixando novamente.")
                    else:
                        log(f"Arquivo {os.path.basename(l_file)} já baixado (tamanho OK). Pulando.")
                        progress(1.0)
                        return

            self.current_downloading_file = l_file
            dl_start_time = time.time()
            last_u_time = 0

            def file_progress_cb(dl_bytes, total_bytes):
                nonlocal last_u_time
                check_pause_and_cancel()
                now = time.time()
                if now - last_u_time >= 0.1 or (total_bytes > 0 and dl_bytes >= total_bytes):
                    last_u_time = now
                    elapsed = max(now - dl_start_time, 0.001)
                    speed = dl_bytes / elapsed

                    if speed >= 1024 * 1024:
                        speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
                    elif speed >= 1024:
                        speed_str = f"{speed / 1024:.1f} KB/s"
                    else:
                        speed_str = f"{speed:.0f} B/s"

                    if total_bytes > 0:
                        pct = dl_bytes / total_bytes
                        pct_str = f"{pct * 100:.1f}%"
                        progress(pct)
                    else:
                        pct_str = "..."

                    fname = os.path.basename(l_file)
                    st_txt = f"Baixando {fname} - {pct_str} ({speed_str})"
                    status(st_txt)

            client_inst.download_file(r_file, l_file, file_progress_cb, size)
            check_pause_and_cancel()
            self.current_downloading_file = None

        try:
            c = self.app_config
            today_str = datetime.now().strftime("%d%m%Y")
            atualiza_path = c["atualizacao_path_win"] if self.os_type == "Windows" else c["atualizacao_path_linux"]
            nbs_path = c["nbs_path_win"] if self.os_type == "Windows" else c["nbs_path_linux"]

            base_dir = os.path.join(atualiza_path, today_str)
            backup_dir = os.path.join(base_dir, "backup")
            modules_dir = os.path.join(base_dir, "Modulos")

            os.makedirs(base_dir, exist_ok=True)
            log("--- INICIANDO PROCESSO ---")
            log(f"Pasta de atualização do dia: {base_dir}")

            # 1. Limpeza de pastas antigas em C:\Atualizacao (max 2)
            utils.cleanup_old_update_folders(atualiza_path, log_callback=log, max_folders=2)

            # 2. Local Backup
            compress_enabled = c.get("compress_backup", False)
            if utils.is_backup_up_to_date(nbs_path, backup_dir, compress_enabled):
                log("Backup já existente e idêntico. Pulando.")
            else:
                status("Fazendo backup de executáveis locais...")
                utils.backup_local_executables(nbs_path, backup_dir, log_callback=log)
                if compress_enabled:
                    log("Compactando backup (.zip)...")
                    zip_p = utils.compress_folder(backup_dir, 'zip', log_callback=log)
                    if zip_p and c.get("delete_backup_after_compress", False):
                        import shutil
                        shutil.rmtree(backup_dir, ignore_errors=True)

            cutoff_date = None if self.initial_installation_var.isChecked() else utils.parse_date(self.cutoff_date_entry.text())
            os.makedirs(modules_dir, exist_ok=True)

            # 3. Download Official Modules
            if self.download_nbs_var.isChecked():
                status("Conectando ao FTP de Módulos...")
                m_host, m_port, m_path = ftp_client.parse_ftp_url(c["ftp_modules_url"])
                
                with ftp_client.FTPClient(m_host, m_port, c["ftp_user"], c["ftp_password"]) as client:
                    log("Conectado no FTP de Módulos com sucesso.")
                    status("Obtendo listagem de módulos...")
                    files = client.list_files_with_info(m_path)
                    
                    files_to_download = [
                        f for f in files
                        if f["modified"] is None or cutoff_date is None or f["modified"] >= cutoff_date
                    ]

                    log(f"Total de módulos encontrados: {len(files)}")
                    log(f"Módulos para download (após {cutoff_date.strftime('%d/%m/%Y') if cutoff_date else 'início'}): {len(files_to_download)}")

                    for i, f in enumerate(files_to_download):
                        remote_file = f"{m_path.rstrip('/')}/{f['name']}"
                        local_file = os.path.join(modules_dir, f["name"])
                        status(f"Baixando módulo ({i+1}/{len(files_to_download)}): {f['name']}")
                        log(f"Baixando {f['name']} (Modificação: {f['modified'].strftime('%d/%m/%Y %H:%M') if f['modified'] else 'Desconhecida'})")
                        download_with_control(client, remote_file, local_file, f["size"])
                    log("Módulos baixados.")

            # 4. Download interfaces/especificas (Always downloaded with modules)
            try:
                log("Iniciando download dos módulos de interfaces/especificas...")
                status("Obtendo listagem de interfaces/especificas...")
                int_host, int_port, int_path = ftp_client.parse_ftp_url(c["ftp_interfaces_url"])
                especificas_remote_dir = f"{int_path.rstrip('/')}/especificas"
                
                with ftp_client.FTPClient(int_host, int_port, c["ftp_user"], c["ftp_password"]) as esp_client:
                    esp_files = esp_client.list_files_with_info(especificas_remote_dir)
                    esp_to_dl = [
                        ef for ef in esp_files 
                        if ef["modified"] is None or cutoff_date is None or ef["modified"] >= cutoff_date
                    ]
                    log(f"Interfaces/especificas: {len(esp_to_dl)} de {len(esp_files)} arquivos para download")
                    for ei, ef in enumerate(esp_to_dl):
                        r_esp_path = f"{especificas_remote_dir}/{ef['name']}"
                        l_esp_path = os.path.join(modules_dir, ef["name"])
                        status(f"Baixando especificas ({ei+1}/{len(esp_to_dl)}): {ef['name']}")
                        download_with_control(esp_client, r_esp_path, l_esp_path, ef["size"])
                    log("Arquivos de interfaces/especificas baixados.")
            except Exception as esp_err:
                log(f"Aviso ao baixar interfaces/especificas: {esp_err}")

            # 5. Download DLLs if Initial Installation checked
            if self.initial_installation_var.isChecked():
                log("Iniciando download das DLLs em /sistemadelphi/modulos/dll...")
                status("Conectando ao FTP de DLLs...")
                dll_host, dll_port, dll_path = ftp_client.parse_ftp_url(c.get("ftp_dll_url", "ftp://nbsi.com.br/sistemadelphi/modulos/dll"))
                
                with ftp_client.FTPClient(dll_host, dll_port, c["ftp_user"], c["ftp_password"]) as dll_client:
                    status("Obtendo listagem de DLLs...")
                    dll_files = dll_client.list_files_with_info(dll_path)
                    log(f"Encontrados {len(dll_files)} arquivos de DLL para baixar.")
                    for di, df in enumerate(dll_files):
                        r_dll_path = f"{dll_path.rstrip('/')}/{df['name']}"
                        l_dll_path = os.path.join(modules_dir, df["name"])
                        status(f"Baixando DLL ({di+1}/{len(dll_files)}): {df['name']}")
                        download_with_control(dll_client, r_dll_path, l_dll_path, df["size"])
                    log("Todos os arquivos de DLL foram baixados.")

            # 6. Download Selected Brand Interfaces
            if self.download_interfaces_var.isChecked():
                selected_brands = [brand for brand, chk in self.brand_checkboxes.items() if chk.isChecked()]
                if selected_brands:
                    log("Iniciando download de interfaces de marcas...")
                    int_host, int_port, int_path = ftp_client.parse_ftp_url(c["ftp_interfaces_url"])
                    
                    with ftp_client.FTPClient(int_host, int_port, c["ftp_user"], c["ftp_password"]) as int_client:
                        for brand in selected_brands:
                            log(f"Processando marca: {brand}")
                            status(f"Buscando arquivos da marca: {brand}")
                            brand_remote_dir = f"{int_path.rstrip('/')}/{brand}"
                            try:
                                brand_files = int_client.list_files_with_info(brand_remote_dir)
                                brand_files_to_dl = [
                                    bf for bf in brand_files 
                                    if bf["modified"] is None or cutoff_date is None or bf["modified"] >= cutoff_date
                                ]
                                log(f"Marca {brand}: {len(brand_files_to_dl)} de {len(brand_files)} arquivos para download")
                                for bi, bf in enumerate(brand_files_to_dl):
                                    r_path = f"{brand_remote_dir}/{bf['name']}"
                                    l_path = os.path.join(modules_dir, bf["name"])
                                    status(f"Baixando {brand} ({bi+1}/{len(brand_files_to_dl)}): {bf['name']}")
                                    download_with_control(int_client, r_path, l_path, bf["size"])
                            except Exception as b_err:
                                log(f"Erro ao baixar arquivos da marca {brand}: {b_err}")

            # 7. Download Scripts
            if self.download_scripts_var.isChecked():
                log("Conectando ao FTP de Scripts...")
                sc_host, sc_port, sc_path = ftp_client.parse_ftp_url(c["ftp_scripts_url"])
                
                with ftp_client.FTPClient(sc_host, sc_port, c["ftp_user"], c["ftp_password"]) as sc_client:
                    status("Buscando script mais recente...")
                    script_files = sc_client.list_files_with_info(sc_path)
                    versioned_scripts = []
                    version_pattern = re.compile(r'^NBSScripts_\d+\.\d+\.\d+\.\d+\.exe$', re.IGNORECASE)
                    
                    for sf in script_files:
                        if version_pattern.match(sf["name"]):
                            versioned_scripts.append(sf)
                            
                    if versioned_scripts:
                        versioned_scripts.sort(key=lambda x: x["modified"] or datetime.min, reverse=True)
                        newest_script = versioned_scripts[0]
                        log(f"Script mais recente identificado: {newest_script['name']}")
                        status(f"Baixando script: {newest_script['name']}")
                        remote_sc = f"{sc_path.rstrip('/')}/{newest_script['name']}"
                        local_sc = os.path.join(base_dir, newest_script["name"])
                        download_with_control(sc_client, remote_sc, local_sc, newest_script["size"])
                        log(f"Script {newest_script['name']} baixado.")
                        if hasattr(self, 'script_path_entry'):
                            norm_sc = os.path.normpath(local_sc)
                            QTimer.singleShot(0, lambda p=norm_sc: self.script_path_entry.setText(p))

                    else:
                        log("Nenhum script versionado (NBSScripts_X.X.X.X.exe) encontrado no FTP de scripts.")

            # 8. Download NFE
            if self.download_nfe_var.isChecked():
                log("Conectando ao FTP NFE...")
                nfe_host, nfe_port, nfe_path = ftp_client.parse_ftp_url(c["ftp_nfe_url"])
                with ftp_client.FTPClient(nfe_host, nfe_port, c["ftp_user"], c["ftp_password"]) as nfe_client:
                    status("Obtendo listagem NFE...")
                    nfe_files = nfe_client.list_files_with_info(nfe_path)
                    nfe_files_to_dl = [
                        nf for nf in nfe_files
                        if nf["modified"] is None or cutoff_date is None or nf["modified"] >= cutoff_date
                    ]
                    log(f"NFE: {len(nfe_files_to_dl)} de {len(nfe_files)} arquivos para download")
                    for ni, nf in enumerate(nfe_files_to_dl):
                        r_nfe_path = f"{nfe_path.rstrip('/')}/{nf['name']}"
                        l_nfe_path = os.path.join(base_dir, nf["name"])
                        status(f"Baixando NFE ({ni+1}/{len(nfe_files_to_dl)}): {nf['name']}")
                        download_with_control(nfe_client, r_nfe_path, l_nfe_path, nf["size"])


            status("Processo finalizado com sucesso!")
            log("--- PROCESSO CONCLUÍDO COM SUCESSO ---")
            progress(1.0)
            if hasattr(self, 'auto_detect_execution_files'):
                QTimer.singleShot(0, self.auto_detect_execution_files)
            if hasattr(self, "dl_finished_signal"):
                self.dl_finished_signal.emit(True, "Sucesso")


        except Exception as e:
            log(f"ERRO durante o processo: {e}")
            status(f"Erro durante a execução: {e}")
            if hasattr(self, "dl_finished_signal"):
                self.dl_finished_signal.emit(False, str(e))



    def _execute_scripts_in_dir(self, directory, log_fn):
        log_fn("Procurando scripts SQL para execução...")
        c = self.app_config
        db_user = c.get("db_user", "")
        db_pass = c.get("db_pass", "")
        db_schema = c.get("db_schema", "")

        for root, _, files in os.walk(directory):
            for f in sorted(files):
                if f.lower().endswith(".sql"):
                    sql_path = os.path.join(root, f)
                    log_fn(f"Executando script: {f}")
                    ok = utils.execute_sql_script(sql_path, db_user, db_pass, db_schema, log_callback=log_fn)
                    if ok:
                        log_fn(f"✓ Script {f} executado com sucesso.")
                    else:
                        log_fn(f"❌ Falha ao executar {f}.")

    def _copy_distribution_logic(self, source_dir, log_fn):
        c = self.app_config
        servers = c.get("servers", [])
        if self.copy_local_var.isChecked():
            nbs_path = c.get("nbs_path_win", "C:\\NBS") if self.os_type == "Windows" else c.get("nbs_path_linux", "./NBS_Local")
            log_fn(f"Copiando arquivos para NBS Local: {nbs_path}...")
            utils.copy_directory_contents(source_dir, nbs_path, log_callback=log_fn)

        if self.copy_servers_var.isChecked():
            for srv in servers:
                if isinstance(srv, dict):
                    ip = srv.get("ip", "")
                    share = srv.get("share", "")
                    user = srv.get("user", "")
                    pwd = srv.get("pass", "")
                else:
                    ip = str(srv)
                    share = "NBS"
                    user = pwd = ""

                target_unc = f"\\\\{ip}\\{share}" if share else f"\\\\{ip}"
                log_fn(f"Distribuindo para {target_unc}...")
                if user:
                    utils.authenticate_smb_session(ip, share, user, pwd, log_callback=log_fn)
                utils.copy_directory_contents(source_dir, target_unc, log_callback=log_fn)

    def run_execute_scripts(self):
        self.exec_log_box.clear()
        threading.Thread(target=self._execute_scripts_thread, daemon=True).start()

    def _execute_scripts_thread(self):
        log = lambda msg: QTimer.singleShot(0, lambda: self.exec_log_box.append(msg))
        c = self.app_config
        today_str = datetime.now().strftime("%d%m%Y")
        atualiza_path = c["atualizacao_path_win"] if self.os_type == "Windows" else c["atualizacao_path_linux"]
        base_dir = os.path.join(atualiza_path, today_str)

        log("--- EXECUÇÃO MANUAL DE SCRIPTS SQL ---")
        self._execute_scripts_in_dir(base_dir, log)

    def run_copy_distribution(self):
        self.dist_log_box.clear()
        threading.Thread(target=self._copy_distribution_thread, daemon=True).start()

    def _copy_distribution_thread(self):
        log = lambda msg: QTimer.singleShot(0, lambda: self.dist_log_box.append(msg))
        c = self.app_config
        today_str = datetime.now().strftime("%d%m%Y")
        atualiza_path = c["atualizacao_path_win"] if self.os_type == "Windows" else c["atualizacao_path_linux"]
        base_dir = os.path.join(atualiza_path, today_str)

        log("--- DISTRIBUIÇÃO MANUAL PARA SERVIDORES ---")
        self._copy_distribution_logic(base_dir, log)

    def run_crm_gold(self):
        cmd = self.crm_gold_cmd_entry.text().strip() if hasattr(self, 'crm_gold_cmd_entry') else "C:\\Java\\Update_BSC_CRMGold\\WEUpdate.exe -suporte"
        if not cmd:
            cmd = "C:\\Java\\Update_BSC_CRMGold\\WEUpdate.exe -suporte"
        try:
            import subprocess
            subprocess.Popen(cmd, shell=True)
            self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Executando CRM Gold: {cmd}")
        except Exception as e:
            self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Erro ao executar CRM Gold: {e}")

    def run_crm_parts(self):
        cmd = self.crm_parts_cmd_entry.text().strip() if hasattr(self, 'crm_parts_cmd_entry') else "C:\\Java\\JManagerClient\\JManagerClient.exe -suporte -disablehash"
        if not cmd:
            cmd = "C:\\Java\\JManagerClient\\JManagerClient.exe -suporte -disablehash"
        try:
            import subprocess
            subprocess.Popen(cmd, shell=True)
            self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Executando CRM Parts / Service: {cmd}")
        except Exception as e:
            self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Erro ao executar CRM Parts: {e}")

    def check_payara_status(self):
        srv_name = self.crm_payara_entry.text().strip() if hasattr(self, 'crm_payara_entry') else "domain1"
        if not srv_name:
            srv_name = "domain1"
        self.lbl_payara_status.setText("VERIFICANDO...")
        self.lbl_payara_status.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")

        def _check():
            is_running = False
            if self.os_type == "Windows":
                try:
                    import subprocess
                    out = subprocess.check_output(f'sc query "{srv_name}"', shell=True, stderr=subprocess.STDOUT).decode(errors="ignore")
                    if "RUNNING" in out.upper():
                        is_running = True
                except Exception:
                    pass
                if not is_running:
                    try:
                        import subprocess
                        out = subprocess.check_output('tasklist /FI "IMAGENAME eq java.exe"', shell=True, stderr=subprocess.STDOUT).decode(errors="ignore")
                        if "JAVA" in out.upper():
                            is_running = True
                    except Exception:
                        pass

            def _update():
                if is_running:
                    self.lbl_payara_status.setText("EM EXECUÇÃO")
                    self.lbl_payara_status.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
                    self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Status do Serviço Payara ({srv_name}): EM EXECUÇÃO (ONLINE)")
                else:
                    self.lbl_payara_status.setText("PARADO / OFF")
                    self.lbl_payara_status.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
                    self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Status do Serviço Payara ({srv_name}): PARADO")

            QTimer.singleShot(0, _update)

        threading.Thread(target=_check, daemon=True).start()

    def start_payara_service(self):
        srv_name = self.crm_payara_entry.text().strip() if hasattr(self, 'crm_payara_entry') else "domain1"
        if not srv_name:
            srv_name = "domain1"
        self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando comando para iniciar o Serviço Payara ({srv_name})...")
        def _start():
            ok = utils.manage_windows_service(srv_name, "start", log_callback=lambda msg: QTimer.singleShot(0, lambda: self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")))
            QTimer.singleShot(1000, self.check_payara_status)
        threading.Thread(target=_start, daemon=True).start()

    def stop_payara_service(self):
        srv_name = self.crm_payara_entry.text().strip() if hasattr(self, 'crm_payara_entry') else "domain1"
        if not srv_name:
            srv_name = "domain1"
        self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando comando para parar o Serviço Payara ({srv_name})...")
        def _stop():
            ok = utils.manage_windows_service(srv_name, "stop", log_callback=lambda msg: QTimer.singleShot(0, lambda: self.crm_log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")))
            QTimer.singleShot(1000, self.check_payara_status)
        threading.Thread(target=_stop, daemon=True).start()



    def open_folder_explorer(self, target):
        c = self.app_config
        if target == "nbs":
            path = c.get("nbs_path_win", "C:\\NBS") if self.os_type == "Windows" else c.get("nbs_path_linux", "./NBS_Local")
        else:
            path = c.get("atualizacao_path_win", "C:\\Atualizacao") if self.os_type == "Windows" else c.get("atualizacao_path_linux", "./Atualizacao")

        os.makedirs(path, exist_ok=True)
        if self.os_type == "Windows":
            os.startfile(path)
        else:
            import subprocess
            subprocess.run(["xdg-open", path])

    def open_taskschd(self):
        if self.os_type == "Windows":
            import subprocess
            subprocess.Popen("taskschd.msc", shell=True)
