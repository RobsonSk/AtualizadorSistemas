import os
import sys
import platform
import threading
import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QMessageBox, QGroupBox
)

import config
import utils
from ui_nbs import NBSMixin, set_entry_text, get_entry_text
from ui_apollo import ApolloMixin
from ui_common import CommonMixin
from license_gatekeeper import enforce_license_gatekeeper, start_background_license_checker


DARK_QSS = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #89b4fa;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QLineEdit, QTextEdit, QComboBox, QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}
QProgressBar {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}
QScrollBar:vertical {
    background: #181825;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
}
"""


class AtualizadorApp(QMainWindow, NBSMixin, ApolloMixin, CommonMixin):
    brands_fetched_signal = Signal(list)
    brands_failed_signal = Signal(str)
    log_debug_signal = Signal(str)
    dl_log_signal = Signal(str)
    dl_status_signal = Signal(str)
    dl_progress_signal = Signal(int)
    dl_finished_signal = Signal(bool, str)
    exec_log_signal = Signal(str)
    exec_status_signal = Signal(str)
    exec_finished_signal = Signal(bool, str)
    linx_dl_log_signal = Signal(str)
    linx_dl_status_signal = Signal(str)
    linx_dl_progress_signal = Signal(int)
    linx_dl_finished_signal = Signal(bool, str)
    linx_update_log_signal = Signal(str)
    linx_update_status_signal = Signal(str)
    linx_update_progress_signal = Signal(int)
    linx_update_finished_signal = Signal(bool, str)
    linx_services_refreshed_signal = Signal(dict)
    show_info_dialog_signal = Signal(str, str)
    show_warning_dialog_signal = Signal(str, str)

    def __init__(self):
        super().__init__()

        # Connect Qt thread signals to UI slots
        self.brands_fetched_signal.connect(self.on_brands_fetched_success)
        self.brands_failed_signal.connect(self.on_brands_fetched_failed)
        self.log_debug_signal.connect(self.append_log_debug_ui)
        self.dl_log_signal.connect(self.log_dl_ui)
        self.dl_status_signal.connect(self.status_dl_ui)
        self.dl_progress_signal.connect(self.progress_dl_ui)
        self.dl_finished_signal.connect(self.on_download_process_finished)
        self.exec_log_signal.connect(self.log_exec_ui)
        self.exec_status_signal.connect(self.status_exec_ui)
        self.exec_finished_signal.connect(self.on_script_execution_finished)
        self.linx_dl_log_signal.connect(self.log_linx_dl_ui)
        self.linx_dl_status_signal.connect(self.status_linx_dl_ui)
        self.linx_dl_progress_signal.connect(self.progress_linx_dl_ui)
        self.linx_dl_finished_signal.connect(self.on_linx_download_finished)
        self.linx_update_log_signal.connect(self.log_linx_update_ui)
        self.linx_update_status_signal.connect(self.status_linx_update_ui)
        self.linx_update_progress_signal.connect(self.progress_linx_update_ui)
        self.linx_update_finished_signal.connect(self.on_linx_update_finished)
        self.linx_services_refreshed_signal.connect(self.on_services_refreshed)
        self.show_info_dialog_signal.connect(lambda title, msg: QMessageBox.information(self, title, msg))
        self.show_warning_dialog_signal.connect(lambda title, msg: QMessageBox.warning(self, title, msg))







        self.app_config = config.load_config()
        self.os_type = platform.system()
        self.loading_config = False

        # Periodic background license checker
        start_background_license_checker(self, "AtualizadorSistemas")

        self.setWindowTitle("Atualizador Sistemas")
        self.resize(1020, 700)
        self.setMinimumSize(950, 640)

        # Main Central Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ----------------- SIDEBAR -----------------
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebar")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.logo_label = QLabel("NBS Atualizador")
        self.logo_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa;")
        self.os_label = QLabel(f"S.O.: {self.os_type}")
        self.os_label.setStyleSheet("font-size: 11px; font-style: italic; color: #a6adc8;")

        self.sidebar_layout.addWidget(self.logo_label)
        self.sidebar_layout.addWidget(self.os_label)
        self.sidebar_layout.addSpacing(15)

        # NBS Navigation Buttons
        self.nav_btn1 = QPushButton("Download & Backup")
        self.nav_btn2 = QPushButton("Executar Scripts")
        self.nav_btn3 = QPushButton("Cópia Servidores")
        self.nav_btn6 = QPushButton("Utilitários NBS")
        self.nav_btn7 = QPushButton("Atualização CRMWeb")
        self.nav_btn4 = QPushButton("Configurações")
        self.nav_btn5 = QPushButton("Sobre o App")
        self.nav_btn_notes = QPushButton("📝 Observações")

        self.nav_btn1.clicked.connect(lambda: self.select_frame("download"))
        self.nav_btn2.clicked.connect(lambda: self.select_frame("execution"))
        self.nav_btn3.clicked.connect(lambda: self.select_frame("distribution"))
        self.nav_btn6.clicked.connect(lambda: self.select_frame("utilities"))
        self.nav_btn7.clicked.connect(lambda: self.select_frame("crmweb"))
        self.nav_btn4.clicked.connect(lambda: self.select_frame("settings"))
        self.nav_btn5.clicked.connect(lambda: self.select_frame("about"))
        self.nav_btn_notes.clicked.connect(lambda: self.select_frame("nbs_notes"))

        self.nbs_nav_buttons = [
            self.nav_btn1, self.nav_btn2, self.nav_btn3,
            self.nav_btn6, self.nav_btn7, self.nav_btn4,
            self.nav_btn5, self.nav_btn_notes
        ]

        for btn in self.nbs_nav_buttons:
            self.sidebar_layout.addWidget(btn)

        # Linx Navigation Buttons
        self.linx_nav_btn_download = QPushButton("Download Linx")
        self.linx_nav_btn_update = QPushButton("Atualização Linx")
        self.linx_nav_btn_utilities = QPushButton("Utilitários Linx")
        self.linx_nav_btn_settings = QPushButton("Configurações Linx")
        self.linx_nav_btn_about = QPushButton("Sobre o Linx")
        self.linx_nav_btn_notes = QPushButton("📝 Observações Linx")

        self.linx_nav_btn_download.clicked.connect(lambda: self.select_frame("linx_download"))
        self.linx_nav_btn_update.clicked.connect(lambda: self.select_frame("linx_update"))
        self.linx_nav_btn_utilities.clicked.connect(lambda: self.select_frame("linx_utilities"))
        self.linx_nav_btn_settings.clicked.connect(lambda: self.select_frame("linx_settings"))
        self.linx_nav_btn_about.clicked.connect(lambda: self.select_frame("linx_about"))
        self.linx_nav_btn_notes.clicked.connect(lambda: self.select_frame("linx_notes"))

        self.linx_nav_buttons = [
            self.linx_nav_btn_download, self.linx_nav_btn_update,
            self.linx_nav_btn_utilities, self.linx_nav_btn_settings,
            self.linx_nav_btn_about, self.linx_nav_btn_notes
        ]

        for btn in self.linx_nav_buttons:
            self.sidebar_layout.addWidget(btn)
            btn.hide()

        self.sidebar_layout.addStretch(1)

        self.nav_btn_back_to_selection = QPushButton("⬅ Alterar Sistema")
        self.nav_btn_back_to_selection.setStyleSheet("background-color: #313244; font-weight: bold;")
        self.nav_btn_back_to_selection.clicked.connect(self.show_system_selection_screen)
        self.sidebar_layout.addWidget(self.nav_btn_back_to_selection)

        # ----------------- STACKED WIDGET CONTAINER -----------------
        self.stacked_widget = QStackedWidget()

        # 1. System Selection View (Index 0)
        self.frame_system_selection = QWidget()
        self.setup_system_selection_ui()

        # 2. NBS Views
        self.frame_download = QWidget()
        self.frame_execution = QWidget()
        self.frame_distribution = QWidget()
        self.frame_utilities = QWidget()
        self.frame_crmweb = QWidget()
        self.frame_settings = QWidget()
        self.frame_about = QWidget()
        self.frame_nbs_notes = QWidget()

        # 3. Linx Views
        self.frame_linx_download = QWidget()
        self.frame_linx_update = QWidget()
        self.frame_linx_utilities = QWidget()
        self.frame_linx_settings = QWidget()
        self.frame_linx_about = QWidget()
        self.frame_linx_notes = QWidget()

        # Setup tab UIs
        self.setup_tab_download()
        self.setup_tab_execution()
        self.setup_tab_distribution()
        self.setup_tab_utilities()
        self.setup_tab_crmweb()
        self.setup_tab_settings()
        self.setup_tab_about()
        self.setup_tab_nbs_notes()

        self.setup_tab_linx_download()
        self.setup_tab_linx_update()
        self.setup_tab_linx_utilities()
        self.setup_tab_linx_settings()
        self.setup_tab_linx_about()
        self.setup_tab_linx_notes()

        # Add all views to stacked widget
        self.views_map = {
            "selection": self.frame_system_selection,
            "download": self.frame_download,
            "execution": self.frame_execution,
            "distribution": self.frame_distribution,
            "utilities": self.frame_utilities,
            "crmweb": self.frame_crmweb,
            "settings": self.frame_settings,
            "about": self.frame_about,
            "nbs_notes": self.frame_nbs_notes,
            "linx_download": self.frame_linx_download,
            "linx_update": self.frame_linx_update,
            "linx_utilities": self.frame_linx_utilities,
            "linx_settings": self.frame_linx_settings,
            "linx_about": self.frame_linx_about,
            "linx_notes": self.frame_linx_notes
        }

        for name, widget in self.views_map.items():
            self.stacked_widget.addWidget(widget)

        self.main_layout.addWidget(self.sidebar_frame)
        self.main_layout.addWidget(self.stacked_widget, 1)

        # Initialize configurations in GUI fields
        self.load_config_into_ui()
        self.auto_detect_cutoff_date()

        self.show_system_selection_screen()

    def setup_system_selection_ui(self):
        layout = QVBoxLayout(self.frame_system_selection)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Atualizador de Sistemas")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Selecione qual sistema você deseja gerenciar:")
        subtitle.setStyleSheet("font-size: 14px; font-style: italic; color: #a6adc8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        cards_row = QHBoxLayout()
        cards_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # NBS Card
        nbs_card = QGroupBox("Sistema NBS")
        nbs_card.setFixedSize(340, 260)
        nbs_card_layout = QVBoxLayout(nbs_card)

        nbs_desc = QLabel(
            "• Atualização de Módulos (FTP)\n"
            "• Execução de Scripts SQL\n"
            "• Cópia de Redes (Distribuição)\n"
            "• Utilitários & Atualização CRMWeb"
        )
        nbs_desc.setStyleSheet("font-size: 12px; line-height: 1.5;")
        btn_enter_nbs = QPushButton("Atualizar NBS")
        btn_enter_nbs.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        btn_enter_nbs.clicked.connect(lambda: self.enter_system("nbs"))

        nbs_card_layout.addWidget(nbs_desc)
        nbs_card_layout.addStretch(1)
        nbs_card_layout.addWidget(btn_enter_nbs)

        # Linx Card
        linx_card = QGroupBox("Sistema Linx DMS")
        linx_card.setFixedSize(340, 260)
        linx_card_layout = QVBoxLayout(linx_card)

        linx_desc = QLabel(
            "• Downloads de Versões (FTP)\n"
            "• Pacotes DMS, HPE, Toyota...\n"
            "• Suporte a 3 Camadas & Web\n"
            "• Atualização Modularizada"
        )
        linx_desc.setStyleSheet("font-size: 12px; line-height: 1.5;")
        btn_enter_linx = QPushButton("Atualizar Linx DMS")
        btn_enter_linx.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 10px;")
        btn_enter_linx.clicked.connect(lambda: self.enter_system("linx"))

        linx_card_layout.addWidget(linx_desc)
        linx_card_layout.addStretch(1)
        linx_card_layout.addWidget(btn_enter_linx)

        cards_row.addWidget(nbs_card)
        cards_row.addSpacing(20)
        cards_row.addWidget(linx_card)

        layout.addLayout(cards_row)

    def enter_system(self, system_name):
        self.sidebar_frame.show()
        if system_name == "nbs":
            self.setWindowTitle("Atualizador Sistemas - NBS")
            self.logo_label.setText("NBS Atualizador")
            for btn in self.linx_nav_buttons:
                btn.hide()
            for btn in self.nbs_nav_buttons:
                btn.show()
            self.select_frame("download")
        elif system_name == "linx":
            self.setWindowTitle("Atualizador Sistemas - Linx DMS")
            self.logo_label.setText("Linx Atualizador")
            for btn in self.nbs_nav_buttons:
                btn.hide()
            for btn in self.linx_nav_buttons:
                btn.show()
            self.select_frame("linx_download")

    def show_system_selection_screen(self):
        self.setWindowTitle("Atualizador Sistemas - Selecionar Sistema")
        self.sidebar_frame.hide()
        self.stacked_widget.setCurrentWidget(self.frame_system_selection)

    def select_frame(self, name):
        if name in self.views_map:
            self.stacked_widget.setCurrentWidget(self.views_map[name])

    def load_config_into_ui(self):
        c = self.app_config
        self.loading_config = True

        set_entry_text(self.ftp_modules_entry, c.get("ftp_modules_url", ""))
        set_entry_text(self.ftp_scripts_entry, c.get("ftp_scripts_url", ""))
        set_entry_text(self.ftp_nfe_entry, c.get("ftp_nfe_url", ""))
        set_entry_text(self.ftp_interfaces_entry, c.get("ftp_interfaces_url", ""))
        set_entry_text(self.ftp_dll_entry, c.get("ftp_dll_url", ""))
        set_entry_text(self.ftp_user_entry, c.get("ftp_user", ""))
        set_entry_text(self.ftp_pass_entry, c.get("ftp_pass", ""))

        set_entry_text(self.atualiza_path_entry, c.get("atualizacao_path_win", "") if self.os_type == "Windows" else c.get("atualizacao_path_linux", ""))
        set_entry_text(self.nbs_path_entry, c.get("nbs_path_win", "") if self.os_type == "Windows" else c.get("nbs_path_linux", ""))

        set_entry_text(self.db_user_entry, c.get("db_user", ""))
        set_entry_text(self.db_pass_entry, c.get("db_pass", ""))
        set_entry_text(self.db_schema_entry, c.get("db_schema", ""))
        set_entry_text(self.db_name_entry, c.get("db_name", ""))

        self.download_nbs_var.setChecked(c.get("download_nbs", True))
        self.download_scripts_var.setChecked(c.get("download_scripts", True))
        self.download_nfe_var.setChecked(c.get("download_nfe", False))
        self.download_interfaces_var.setChecked(c.get("download_interfaces", False))
        self.initial_installation_var.setChecked(c.get("initial_installation", False))
        self.compress_backup_var.setChecked(c.get("compress_backup", False))
        self.delete_backup_after_compress_var.setChecked(c.get("delete_backup_after_compress", False))
        if hasattr(self, 'debug_mode_var'):
            self.debug_mode_var.setChecked(c.get("debug_mode", False))



        self.copy_local_var.setChecked(c.get("copy_local", True))
        self.copy_servers_var.setChecked(c.get("copy_servers", True))

        set_entry_text(self.crm_gold_cmd_entry, c.get("crm_gold_cmd", "C:\\Java\\Update_BSC_CRMGold\\WEUpdate.exe -suporte"))
        set_entry_text(self.crm_parts_cmd_entry, c.get("crm_parts_cmd", "C:\\Java\\JManagerClient\\JManagerClient.exe -suporte -disablehash"))
        set_entry_text(self.crm_payara_entry, c.get("crm_service_payara", "domain1"))


        # Update visual recaps
        p_up = c.get("atualizacao_path_win", "") if self.os_type == "Windows" else c.get("atualizacao_path_linux", "")
        p_nbs = c.get("nbs_path_win", "") if self.os_type == "Windows" else c.get("nbs_path_linux", "")
        self.recap_atualiza_lbl.setText(f"Atualização: {p_up}")
        self.recap_nbs_lbl.setText(f"NBS Local: {p_nbs}")
        self.recap_ftp_lbl.setText(f"FTP: {c.get('ftp_modules_url', '')}")


        self.refresh_servers_list_ui()

        # Linx configurations
        self.linx_package_menu.setCurrentText(c.get("linx_package", "LINXDMS"))
        set_entry_text(self.linx_version_entry, c.get("linx_version", "v5.19"))
        set_entry_text(self.linx_path_entry, c.get("linx_download_path_win", "") if self.os_type == "Windows" else c.get("linx_download_path_linux", ""))

        self.linx_dl_delphi_var.setChecked(c.get("linx_download_delphi", True))
        self.linx_dl_server_var.setChecked(c.get("linx_download_server", False))
        self.linx_dl_client_var.setChecked(c.get("linx_download_client", False))
        self.linx_dl_web_var.setChecked(c.get("linx_download_web", False))
        self.linx_dl_comissoes_var.setChecked(c.get("linx_download_comissoes", False))
        self.linx_dl_apoio_trocafornec_var.setChecked(c.get("linx_download_apoio_trocafornec", False))
        self.linx_dl_apoio_trocaserie_var.setChecked(c.get("linx_download_apoio_trocaserie", False))
        self.linx_dl_apoio_verificadiaria_var.setChecked(c.get("linx_download_apoio_verificadiaria", False))
        self.linx_dl_integrador_var.setChecked(c.get("linx_download_integrador", False))
        self.linx_backup_apollo_var.setChecked(c.get("linx_backup_apollo", False))

        set_entry_text(self.linx_url_delphi_entry, c.get("linx_url_delphi_template", config.DEFAULT_CONFIG["linx_url_delphi_template"]))
        set_entry_text(self.linx_url_server_entry, c.get("linx_url_server_template", config.DEFAULT_CONFIG["linx_url_server_template"]))
        set_entry_text(self.linx_url_client_entry, c.get("linx_url_client_template", config.DEFAULT_CONFIG["linx_url_client_template"]))
        set_entry_text(self.linx_url_web_entry, c.get("linx_url_web_template", config.DEFAULT_CONFIG["linx_url_web_template"]))
        set_entry_text(self.linx_url_comissoes_delphi_entry, c.get("linx_url_comissoes_delphi_template", config.DEFAULT_CONFIG["linx_url_comissoes_delphi_template"]))
        set_entry_text(self.linx_url_comissoes_client_entry, c.get("linx_url_comissoes_client_template", config.DEFAULT_CONFIG["linx_url_comissoes_client_template"]))
        set_entry_text(self.linx_url_apoio_entry, c.get("linx_url_apoio_template", config.DEFAULT_CONFIG["linx_url_apoio_template"]))
        set_entry_text(self.linx_url_integrador_entry, c.get("linx_url_integrador_template", config.DEFAULT_CONFIG["linx_url_integrador_template"]))

        set_entry_text(self.linx_service_dfe_entry, c.get("linx_service_dfe", "DFeServico"))
        set_entry_text(self.linx_service_datasnap_entry, c.get("linx_service_datasnap", "RedirecionaDatasnap"))
        set_entry_text(self.linx_service_3camadas_entry, c.get("linx_service_3camadas", "VerificaServer3Camadas"))
        set_entry_text(self.linx_service_integrador_entry, c.get("linx_service_integrador", "dmLDIServer"))
        set_entry_text(self.linx_kill_pattern_entry, c.get("linx_kill_process_pattern", "wsContabil"))

        p_norm = c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_normal_linux", "./Apollo_Atualiza")
        p_serv = c.get("linx_path_server_win", "C:\\3Camadas") if self.os_type == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
        p_clit = c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza") if self.os_type == "Windows" else c.get("linx_path_client_linux", "./3Camadas_Atualiza")

        set_entry_text(self.linx_path_normal_entry, p_norm)
        set_entry_text(self.linx_path_server_entry, p_serv)
        set_entry_text(self.linx_path_client_entry, p_clit)

        self.dest_normal_lbl.setText(f"Apollo/Atualiza: {p_norm}")
        self.dest_server_lbl.setText(f"3Camadas Server: {p_serv}")
        self.dest_client_lbl.setText(f"3Camadas Client: {p_clit}")

        if hasattr(self, "nbs_notes_box"):
            self.nbs_notes_box.setPlainText(c.get("nbs_notes", ""))

        self.loading_config = False


    def save_ui_to_config(self):
        if getattr(self, "loading_config", False):
            return
        c = self.app_config

        c["ftp_modules_url"] = get_entry_text(self.ftp_modules_entry)
        c["ftp_scripts_url"] = get_entry_text(self.ftp_scripts_entry)
        c["ftp_nfe_url"] = get_entry_text(self.ftp_nfe_entry)
        c["ftp_interfaces_url"] = get_entry_text(self.ftp_interfaces_entry)
        c["ftp_dll_url"] = get_entry_text(self.ftp_dll_entry)
        c["ftp_user"] = get_entry_text(self.ftp_user_entry)
        c["ftp_pass"] = get_entry_text(self.ftp_pass_entry)

        if self.os_type == "Windows":
            c["atualizacao_path_win"] = get_entry_text(self.atualiza_path_entry)
            c["nbs_path_win"] = get_entry_text(self.nbs_path_entry)
        else:
            c["atualizacao_path_linux"] = get_entry_text(self.atualiza_path_entry)
            c["nbs_path_linux"] = get_entry_text(self.nbs_path_entry)

        c["db_user"] = get_entry_text(self.db_user_entry)
        c["db_pass"] = get_entry_text(self.db_pass_entry)
        c["db_schema"] = get_entry_text(self.db_schema_entry)
        c["db_name"] = get_entry_text(self.db_name_entry)

        c["download_nbs"] = self.download_nbs_var.isChecked()
        c["download_scripts"] = self.download_scripts_var.isChecked()
        c["download_nfe"] = self.download_nfe_var.isChecked()
        c["download_interfaces"] = self.download_interfaces_var.isChecked()
        c["initial_installation"] = self.initial_installation_var.isChecked()
        c["compress_backup"] = self.compress_backup_var.isChecked()
        c["delete_backup_after_compress"] = self.delete_backup_after_compress_var.isChecked()
        if hasattr(self, 'debug_mode_var'):
            c["debug_mode"] = self.debug_mode_var.isChecked()

        if hasattr(self, 'brand_checkboxes') and self.brand_checkboxes:
            c["selected_interfaces"] = [brand for brand, chk in self.brand_checkboxes.items() if chk.isChecked()]

        if hasattr(self, "nbs_notes_box"):
            c["nbs_notes"] = self.nbs_notes_box.toPlainText()

        c["copy_local"] = self.copy_local_var.isChecked()


        c["copy_servers"] = self.copy_servers_var.isChecked()

        c["crm_gold_cmd"] = get_entry_text(self.crm_gold_cmd_entry)
        c["crm_parts_cmd"] = get_entry_text(self.crm_parts_cmd_entry)
        c["crm_service_payara"] = get_entry_text(self.crm_payara_entry)



        c["linx_package"] = self.linx_package_menu.currentText()
        c["linx_version"] = get_entry_text(self.linx_version_entry)
        if self.os_type == "Windows":
            c["linx_download_path_win"] = get_entry_text(self.linx_path_entry)
        else:
            c["linx_download_path_linux"] = get_entry_text(self.linx_path_entry)

        c["linx_download_delphi"] = self.linx_dl_delphi_var.isChecked()
        c["linx_download_server"] = self.linx_dl_server_var.isChecked()
        c["linx_download_client"] = self.linx_dl_client_var.isChecked()
        c["linx_download_web"] = self.linx_dl_web_var.isChecked()
        c["linx_download_comissoes"] = self.linx_dl_comissoes_var.isChecked()
        c["linx_download_apoio_trocafornec"] = self.linx_dl_apoio_trocafornec_var.isChecked()
        c["linx_download_apoio_trocaserie"] = self.linx_dl_apoio_trocaserie_var.isChecked()
        c["linx_download_apoio_verificadiaria"] = self.linx_dl_apoio_verificadiaria_var.isChecked()
        c["linx_download_integrador"] = self.linx_dl_integrador_var.isChecked()
        c["linx_backup_apollo"] = self.linx_backup_apollo_var.isChecked()

        c["linx_url_delphi_template"] = get_entry_text(self.linx_url_delphi_entry)
        c["linx_url_server_template"] = get_entry_text(self.linx_url_server_entry)
        c["linx_url_client_template"] = get_entry_text(self.linx_url_client_entry)
        c["linx_url_web_template"] = get_entry_text(self.linx_url_web_entry)
        c["linx_url_comissoes_delphi_template"] = get_entry_text(self.linx_url_comissoes_delphi_entry)
        c["linx_url_comissoes_client_template"] = get_entry_text(self.linx_url_comissoes_client_entry)
        c["linx_url_apoio_template"] = get_entry_text(self.linx_url_apoio_entry)
        c["linx_url_integrador_template"] = get_entry_text(self.linx_url_integrador_entry)

        c["linx_service_dfe"] = get_entry_text(self.linx_service_dfe_entry)
        c["linx_service_datasnap"] = get_entry_text(self.linx_service_datasnap_entry)
        c["linx_service_3camadas"] = get_entry_text(self.linx_service_3camadas_entry)
        c["linx_service_integrador"] = get_entry_text(self.linx_service_integrador_entry)
        c["linx_kill_process_pattern"] = get_entry_text(self.linx_kill_pattern_entry)

        if self.os_type == "Windows":
            c["linx_path_normal_win"] = get_entry_text(self.linx_path_normal_entry)
            c["linx_path_server_win"] = get_entry_text(self.linx_path_server_entry)
            c["linx_path_client_win"] = get_entry_text(self.linx_path_client_entry)
        else:
            c["linx_path_normal_linux"] = get_entry_text(self.linx_path_normal_entry)
            c["linx_path_server_linux"] = get_entry_text(self.linx_path_server_entry)
            c["linx_path_client_linux"] = get_entry_text(self.linx_path_client_entry)

        config.save_config(c)
        if hasattr(self, "update_linx_paths_display"):
            self.update_linx_paths_display()


    def closeEvent(self, event):
        try:
            self.save_ui_to_config()
        except Exception:
            pass
        event.accept()

    def on_license_revoked(self):
        QMessageBox.critical(
            self,
            "Licença Revogada",
            "A licença deste sistema foi revogada ou expirou no servidor REST.\nO aplicativo será encerrado."
        )
        self.close()
        sys.exit(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)

    # 🔒 GATEKEEPER: Se a licença não for aprovada online, encerra o programa na hora
    if not enforce_license_gatekeeper("AtualizadorSistemas"):
        sys.exit(0)

    # 🟢 ACESSO LIBERADO: Carrega a aplicação PySide6
    try:
        main_win = AtualizadorApp()
        main_win.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Erro ao inicializar interface gráfica: {str(e)}")
        sys.exit(1)
