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
    QProgressBar, QGroupBox, QScrollArea, QMessageBox, QFileDialog, QFrame
)

import config
import utils
from changelog import CHANGELOG_APOLLO
from ui_common import CTkToolTip
from license_gatekeeper import LicenseManager, LicenseActivationDialog, get_hwid


def set_entry_text(widget, text):
    if widget is not None:
        widget.setText(str(text) if text is not None else "")


def get_entry_text(widget):
    if widget is not None:
        return widget.text().strip()
    return ""


class ApolloMixin:
    """Interface, abas e lógica de negócios específica do sistema Linx DMS / Apollo."""

    def setup_tab_linx_download(self):
        tab = self.frame_linx_download
        layout = QHBoxLayout(tab)

        # Left Column (Download Parameters)
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_left.setWidget(left_widget)

        param_group = QGroupBox("Parâmetros do Linx DMS")
        param_layout = QVBoxLayout(param_group)

        pkg_row = QHBoxLayout()
        pkg_row.addWidget(QLabel("Pacote / Sistema:"))
        self.linx_package_menu = QComboBox()
        self.linx_package_menu.addItems(["LINXDMS", "HPE", "BRAVOS", "TOYOTA"])
        pkg_row.addWidget(self.linx_package_menu, 1)
        param_layout.addLayout(pkg_row)

        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Versão (Ex: v5.19):"))
        self.linx_version_entry = QLineEdit("5.19")
        ver_row.addWidget(self.linx_version_entry, 1)
        param_layout.addLayout(ver_row)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Pasta Destino Download:"))
        self.linx_path_entry = QLineEdit()
        btn_browse_linx = QPushButton("...")
        btn_browse_linx.setFixedWidth(40)
        btn_browse_linx.clicked.connect(lambda: self.browse_directory(self.linx_path_entry))
        path_row.addWidget(self.linx_path_entry, 1)
        path_row.addWidget(btn_browse_linx)
        param_layout.addLayout(path_row)

        param_layout.addWidget(QLabel("Módulos para Download:"))
        self.linx_dl_delphi_var = QCheckBox("Delphi (Download Padrão)")
        self.linx_dl_delphi_var.setChecked(True)
        self.linx_dl_server_var = QCheckBox("3 Camadas - Server")
        self.linx_dl_client_var = QCheckBox("3 Camadas - Client")
        self.linx_dl_web_var = QCheckBox("Instalador Web (LinxDMS Web)")
        self.linx_dl_comissoes_var = QCheckBox("DMS Comissões")
        self.linx_dl_apoio_trocafornec_var = QCheckBox("Apoio - Troca Fornecedor")
        self.linx_dl_apoio_trocaserie_var = QCheckBox("Apoio - Troca Série Transm.")
        self.linx_dl_apoio_verificadiaria_var = QCheckBox("Apoio - Verifica Comp. Diária")
        self.linx_dl_integrador_var = QCheckBox("Linx DMS Integrador")
        self.linx_backup_apollo_var = QCheckBox("Backup EXE e DLLs (C:\\Apollo\\atualiza) antes de descompactar")

        param_layout.addWidget(self.linx_dl_delphi_var)
        param_layout.addWidget(self.linx_dl_server_var)
        param_layout.addWidget(self.linx_dl_client_var)
        param_layout.addWidget(self.linx_dl_web_var)
        param_layout.addWidget(self.linx_dl_comissoes_var)
        param_layout.addWidget(self.linx_dl_apoio_trocafornec_var)
        param_layout.addWidget(self.linx_dl_apoio_trocaserie_var)
        param_layout.addWidget(self.linx_dl_apoio_verificadiaria_var)
        param_layout.addWidget(self.linx_dl_integrador_var)
        param_layout.addWidget(self.linx_backup_apollo_var)

        left_layout.addWidget(param_group)

        # Right Column (Logs & Action)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.linx_dl_status_label = QLabel("Status: Aguardando download...")
        self.linx_dl_status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa;")

        self.linx_dl_progressbar = QProgressBar()
        self.linx_dl_progressbar.setRange(0, 100)

        self.linx_dl_log_box = QTextEdit()
        self.linx_dl_log_box.setReadOnly(True)
        self.linx_dl_log_box.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #181825; color: #cdd6f4; border: 1px solid #45475a;")

        btn_row = QHBoxLayout()
        self.btn_run_linx_download = QPushButton("Iniciar Processo")
        self.btn_run_linx_download.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_linx_download.clicked.connect(self.run_linx_download)

        self.btn_pause_linx_download = QPushButton("Pausar")
        self.btn_pause_linx_download.setEnabled(False)
        self.btn_pause_linx_download.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 10px;")
        self.btn_pause_linx_download.clicked.connect(self.toggle_linx_pause_download)

        self.btn_cancel_linx_download = QPushButton("Cancelar")
        self.btn_cancel_linx_download.setEnabled(False)
        self.btn_cancel_linx_download.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 10px;")
        self.btn_cancel_linx_download.clicked.connect(self.cancel_linx_download)

        btn_row.addWidget(self.btn_run_linx_download, 2)
        btn_row.addWidget(self.btn_pause_linx_download, 1)
        btn_row.addWidget(self.btn_cancel_linx_download, 1)

        right_layout.addWidget(self.linx_dl_status_label)
        right_layout.addWidget(self.linx_dl_progressbar)
        right_layout.addWidget(self.linx_dl_log_box, 1)
        right_layout.addLayout(btn_row)

        layout.addWidget(scroll_left, 1)
        layout.addWidget(right_widget, 1)


    def update_linx_paths_display(self):
        c = getattr(self, "app_config", {})
        p_norm = c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_normal_linux", "./Apollo_Atualiza")
        p_serv = c.get("linx_path_server_win", "C:\\3Camadas") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
        p_clit = c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_client_linux", "./3Camadas_Atualiza")

        if hasattr(self, "dest_normal_lbl"):
            self.dest_normal_lbl.setText(f"Apollo/Atualiza: {p_norm}")
        if hasattr(self, "dest_server_lbl"):
            self.dest_server_lbl.setText(f"3Camadas Server: {p_serv}")
        if hasattr(self, "dest_client_lbl"):
            self.dest_client_lbl.setText(f"3Camadas Client: {p_clit}")

    def setup_tab_linx_update(self):
        tab = self.frame_linx_update
        layout = QHBoxLayout(tab)

        # Left Frame: Windows Services Control Panel
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_left.setWidget(left_widget)

        srv_group = QGroupBox("Serviços do Windows (Monitoramento e Controle em Tempo Real)")
        srv_layout = QVBoxLayout(srv_group)

        self.services_list_container = QWidget()
        self.services_grid = QGridLayout(self.services_list_container)
        srv_layout.addWidget(self.services_list_container)

        self.service_status_labels = {}
        self.service_action_buttons = {}

        self.btn_refresh_services = QPushButton("🔄 Atualizar Status dos Serviços")
        self.btn_refresh_services.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; padding: 6px;")
        self.btn_refresh_services.clicked.connect(self.refresh_linx_services)
        srv_layout.addWidget(self.btn_refresh_services)

        self.btn_stop_apolloserver = QPushButton("Fechar ApolloServer (*serverapp*)")
        self.btn_stop_apolloserver.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 6px;")
        self.btn_stop_apolloserver.clicked.connect(self.stop_apollo_server_process)
        srv_layout.addWidget(self.btn_stop_apolloserver)

        kill_group = QGroupBox("Fechar Processos Específicos (Regex / Nome)")
        kill_layout = QHBoxLayout(kill_group)
        self.linx_kill_pattern_entry = QLineEdit()
        self.linx_kill_pattern_entry.setPlaceholderText("ex: wsContabil ou *serverapp*")
        c = getattr(self, "app_config", {})
        self.linx_kill_pattern_entry.setText(c.get("linx_kill_process_pattern", "wsContabil"))

        btn_stop_custom = QPushButton("Fechar")
        btn_stop_custom.setFixedWidth(80)
        btn_stop_custom.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        btn_stop_custom.clicked.connect(self.stop_process_by_regex)

        kill_layout.addWidget(self.linx_kill_pattern_entry, 1)
        kill_layout.addWidget(btn_stop_custom)
        srv_layout.addWidget(kill_group)

        left_layout.addWidget(srv_group)

        # Right Frame: Extraction & Installation Panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        recap_group = QGroupBox("Diretórios de Destino Configurados")
        recap_layout = QVBoxLayout(recap_group)
        self.dest_normal_lbl = QLabel("Apollo/Atualiza: -")
        self.dest_server_lbl = QLabel("3Camadas Server: -")
        self.dest_client_lbl = QLabel("3Camadas Client: -")
        self.dest_normal_lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self.dest_server_lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self.dest_client_lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")

        recap_layout.addWidget(self.dest_normal_lbl)
        recap_layout.addWidget(self.dest_server_lbl)
        recap_layout.addWidget(self.dest_client_lbl)
        right_layout.addWidget(recap_group)

        self.linx_update_status_label = QLabel("Status: Pronto para aplicar atualização.")
        self.linx_update_status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #89b4fa;")

        self.linx_update_progressbar = QProgressBar()
        self.linx_update_progressbar.setRange(0, 100)

        self.linx_update_log_box = QTextEdit()
        self.linx_update_log_box.setReadOnly(True)
        self.linx_update_log_box.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #181825; color: #cdd6f4; border: 1px solid #45475a;")

        self.btn_run_linx_update = QPushButton("🚀 Iniciar Atualização (Descompactar e Reiniciar Serviços)")
        self.btn_run_linx_update.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_linx_update.clicked.connect(self.run_linx_update)

        right_layout.addWidget(self.linx_update_status_label)
        right_layout.addWidget(self.linx_update_progressbar)
        right_layout.addWidget(self.linx_update_log_box, 1)
        right_layout.addWidget(self.btn_run_linx_update)

        layout.addWidget(scroll_left, 1)
        layout.addWidget(right_widget, 1)

        self.update_linx_paths_display()
        self.build_services_ui()
        self.refresh_linx_services()

    def build_services_ui(self):
        while self.services_grid.count():
            item = self.services_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.service_status_labels.clear()
        self.service_action_buttons.clear()

        c = getattr(self, "app_config", {})
        services = [
            ("dfe", c.get("linx_service_dfe", "DFeServico")),
            ("datasnap", c.get("linx_service_datasnap", "RedirecionaDatasnap")),
            ("3camadas", c.get("linx_service_3camadas", "VerificaServer3Camadas")),
            ("integrador", c.get("linx_service_integrador", "dmLDIServer"))
        ]

        for i, (key, s_name) in enumerate(services):
            lbl_name = QLabel(s_name)
            lbl_name.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 12px;")

            lbl_status = QLabel("CONSULTANDO...")
            lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_status.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
            self.service_status_labels[key] = lbl_status

            btn_action = QPushButton("...")
            btn_action.setFixedWidth(80)
            btn_action.setEnabled(False)
            self.service_action_buttons[key] = btn_action

            self.services_grid.addWidget(lbl_name, i, 0)
            self.services_grid.addWidget(lbl_status, i, 1)
            self.services_grid.addWidget(btn_action, i, 2)

    def refresh_linx_services(self):

        self.build_services_ui()
        if hasattr(self, "btn_refresh_services"):
            self.btn_refresh_services.setEnabled(False)
            self.btn_refresh_services.setText("Consultando...")

        def _bg_thread():
            c = getattr(self, "app_config", {})
            services = {
                "dfe": c.get("linx_service_dfe", "DFeServico"),
                "datasnap": c.get("linx_service_datasnap", "RedirecionaDatasnap"),
                "3camadas": c.get("linx_service_3camadas", "VerificaServer3Camadas"),
                "integrador": c.get("linx_service_integrador", "dmLDIServer")
            }
            statuses = {}
            for key, s_name in services.items():
                statuses[key] = self.query_service_status(s_name)

            if hasattr(self, "linx_services_refreshed_signal"):
                self.linx_services_refreshed_signal.emit(statuses)
            else:
                self.on_services_refreshed(statuses)

        threading.Thread(target=_bg_thread, daemon=True).start()

    def make_service_toggle_handler(self, key, action):
        return lambda: self.trigger_service_toggle(key, action)

    def on_services_refreshed(self, statuses):
        if hasattr(self, "btn_refresh_services"):
            self.btn_refresh_services.setEnabled(True)
            self.btn_refresh_services.setText("🔄 Atualizar Status dos Serviços")

        for key, status_val in statuses.items():
            lbl = self.service_status_labels.get(key)
            btn = self.service_action_buttons.get(key)
            if not lbl or not btn:
                continue

            if status_val == "ONLINE":
                lbl.setText("ONLINE")
                lbl.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
                btn.setEnabled(True)
                btn.setText("Parar")
                btn.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
                try:
                    btn.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(self.make_service_toggle_handler(key, "stop"))
            elif status_val == "OFFLINE":
                lbl.setText("OFFLINE")
                lbl.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
                btn.setEnabled(True)
                btn.setText("Iniciar")
                btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
                try:
                    btn.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(self.make_service_toggle_handler(key, "start"))

            elif status_val == "INDISPONIVEL":
                lbl.setText("APENAS WINDOWS")
                lbl.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
                btn.setEnabled(False)
                btn.setText("Indisponível")
            else:
                lbl.setText("INEXISTENTE")
                lbl.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
                btn.setEnabled(False)
                btn.setText("-")

    def query_service_status(self, service_name):
        if getattr(self, "os_type", "Windows") != "Windows":
            return "INDISPONIVEL"

        import subprocess
        try:
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                creationflags=0x08000000
            )
            stdout_upper = (result.stdout or "").upper()
            has_state_info = any(term in stdout_upper for term in ["STATE", "ESTADO", "STATUS", "STATO", "ETAT"])

            if has_state_info:
                if "RUNNING" in stdout_upper or "4  RUNNING" in stdout_upper:
                    return "ONLINE"
                elif "STOPPED" in stdout_upper or "1  STOPPED" in stdout_upper:
                    return "OFFLINE"

            if "1060" in stdout_upper or "DOES NOT EXIST" in stdout_upper or "NAO EXISTE" in stdout_upper or "NÃO EXISTE" in stdout_upper:
                return "INEXISTENTE"

            return "OFFLINE"
        except Exception:
            return "DESCONHECIDO"

    def trigger_service_toggle(self, key, action):
        c = getattr(self, "app_config", {})
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
            lbl.setText("PROCESSANDO...")
            lbl.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
            btn.setEnabled(False)

        def _toggle_thread():
            if getattr(self, "os_type", "Windows") == "Windows":
                import subprocess
                try:
                    subprocess.run(["sc", action, s_name], capture_output=True, text=True, creationflags=0x08000000)
                    time.sleep(2.0)
                except Exception:
                    pass
            else:
                time.sleep(1.5)

            statuses = {key: self.query_service_status(s_name)}
            if hasattr(self, "linx_services_refreshed_signal"):
                self.linx_services_refreshed_signal.emit(statuses)
            else:
                self.on_services_refreshed(statuses)

        threading.Thread(target=_toggle_thread, daemon=True).start()

    def stop_apollo_server_process(self):
        def run_stop():
            try:
                self.log_linx_update("Solicitação para encerrar processos do ApolloServer (*serverapp*)...")
                if getattr(self, "os_type", "Windows") == "Windows":
                    import subprocess
                    cmd = ["powershell", "-Command", "stop-process -name *serverapp* -Force"]
                    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                    if res.returncode == 0:
                        msg = "Processos do ApolloServer (*serverapp*) encerrados com sucesso!"
                        self.log_linx_update(msg)
                        if hasattr(self, "show_info_dialog_signal"):
                            self.show_info_dialog_signal.emit("Sucesso", msg)
                    else:
                        err_out = res.stderr.strip() or res.stdout.strip() or "Nenhum processo *serverapp* em execução."
                        self.log_linx_update(f"Resultado ApolloServer: {err_out}")
                        if hasattr(self, "show_info_dialog_signal"):
                            self.show_info_dialog_signal.emit("Informação", f"Resultado ApolloServer:\n{err_out}")
                else:
                    msg = "Comando enviado (Simulado): powershell stop-process -name *serverapp*"
                    self.log_linx_update(msg)
                    if hasattr(self, "show_info_dialog_signal"):
                        self.show_info_dialog_signal.emit("Simulação (Linux)", msg)
            except Exception as e:
                self.log_linx_update(f"Erro ao fechar ApolloServer: {e}")
                if hasattr(self, "show_warning_dialog_signal"):
                    self.show_warning_dialog_signal.emit("Erro", f"Erro ao fechar ApolloServer:\n{e}")

        threading.Thread(target=run_stop, daemon=True).start()

    def stop_process_by_regex(self, pattern=None):
        if not pattern or not isinstance(pattern, str):
            pattern = self.linx_kill_pattern_entry.text().strip() if hasattr(self, 'linx_kill_pattern_entry') else "wsContabil"

        if not pattern:
            QMessageBox.warning(self, "Aviso", "Por favor, informe o nome ou padrão Regex do processo a encerrar.")
            return

        def run_kill():
            try:
                self.log_linx_update(f"Solicitação para encerrar processos via Regex/Nome: '{pattern}'...")
                if getattr(self, "os_type", "Windows") == "Windows":
                    import subprocess
                    safe_pattern = pattern.replace("'", "''")
                    ps_cmd = f"Get-Process | Where-Object {{ $_.ProcessName -match '{safe_pattern}' -or $_.Name -like '*{safe_pattern}*' }} | Stop-Process -Force"
                    cmd = ["powershell", "-Command", ps_cmd]
                    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                    if res.returncode == 0:
                        msg = f"Processo(s) correspondente(s) a '{pattern}' encerrado(s) com sucesso!"
                        self.log_linx_update(msg)
                        if hasattr(self, "show_info_dialog_signal"):
                            self.show_info_dialog_signal.emit("Sucesso", msg)
                    else:
                        err_out = res.stderr.strip() or res.stdout.strip() or f"Nenhum processo correspondente a '{pattern}' em execução."
                        self.log_linx_update(f"Resultado do encerramento ({pattern}): {err_out}")
                        if hasattr(self, "show_info_dialog_signal"):
                            self.show_info_dialog_signal.emit("Informação", f"Resultado do encerramento ({pattern}):\n{err_out}")
                else:
                    msg = f"[Linux SIMULADO] Encerrando processos por padrão Regex: '{pattern}'"
                    self.log_linx_update(msg)
                    if hasattr(self, "show_info_dialog_signal"):
                        self.show_info_dialog_signal.emit("Simulação (Linux)", msg)
            except Exception as e:
                self.log_linx_update(f"Erro ao fechar processo ({pattern}): {e}")
                if hasattr(self, "show_warning_dialog_signal"):
                    self.show_warning_dialog_signal.emit("Erro", f"Erro ao fechar processo ({pattern}):\n{e}")

        threading.Thread(target=run_kill, daemon=True).start()


    def setup_tab_linx_utilities(self):

        tab = self.frame_linx_utilities
        layout = QVBoxLayout(tab)

        lbl = QLabel("Utilitários e Ferramentas Linx DMS")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)

        grid_group = QGroupBox("Ações Rápidas")
        grid_layout = QGridLayout(grid_group)

        btn_ext_clean = QPushButton("🧹 Limpeza de Arquivos por Regex / Extensão (Linx)")
        btn_ext_clean.setStyleSheet("padding: 12px; font-weight: bold;")
        btn_ext_clean.clicked.connect(lambda: self.open_extension_cleanup_popup("apollo"))

        CTkToolTip(btn_ext_clean, "Abre a ferramenta de limpeza por extensão de arquivo no diretório Linx.")

        btn_ps_reboot = QPushButton("⚡ Reinício Remoto de Servidor (Linx)")
        btn_ps_reboot.setStyleSheet("padding: 12px; font-weight: bold;")
        btn_ps_reboot.clicked.connect(lambda: self.open_powershell_restart_popup("apollo"))
        CTkToolTip(btn_ps_reboot, "Envia o comando Restart-Computer via PowerShell.")

        btn_open_apollo = QPushButton("📂 Abrir Pasta C:\\Apollo")
        btn_open_apollo.setStyleSheet("padding: 12px;")
        btn_open_apollo.clicked.connect(lambda: self.open_linx_folder("apollo"))

        btn_open_3cam = QPushButton("📂 Abrir Pasta C:\\3camadas")
        btn_open_3cam.setStyleSheet("padding: 12px;")
        btn_open_3cam.clicked.connect(lambda: self.open_linx_folder("3camadas"))

        grid_layout.addWidget(btn_ext_clean, 0, 0)
        grid_layout.addWidget(btn_ps_reboot, 0, 1)
        grid_layout.addWidget(btn_open_apollo, 1, 0)
        grid_layout.addWidget(btn_open_3cam, 1, 1)

        layout.addWidget(grid_group)
        layout.addStretch(1)

    def setup_tab_linx_settings(self):
        tab = self.frame_linx_settings
        layout = QVBoxLayout(tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        # Templates Section
        tmpl_group = QGroupBox("Templates de URLs de Download Linx")
        tmpl_layout = QVBoxLayout(tmpl_group)

        tmpl_layout.addWidget(QLabel("Linx Delphi Template:"))
        self.linx_url_delphi_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_delphi_entry)

        tmpl_layout.addWidget(QLabel("3Camadas Server Template:"))
        self.linx_url_server_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_server_entry)

        tmpl_layout.addWidget(QLabel("3Camadas Client Template:"))
        self.linx_url_client_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_client_entry)

        tmpl_layout.addWidget(QLabel("3Camadas Web Template:"))
        self.linx_url_web_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_web_entry)

        tmpl_layout.addWidget(QLabel("Comissões Delphi Template:"))
        self.linx_url_comissoes_delphi_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_comissoes_delphi_entry)

        tmpl_layout.addWidget(QLabel("Comissões Client Template:"))
        self.linx_url_comissoes_client_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_comissoes_client_entry)

        tmpl_layout.addWidget(QLabel("Apoio Template:"))
        self.linx_url_apoio_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_apoio_entry)

        tmpl_layout.addWidget(QLabel("Integrador Template:"))
        self.linx_url_integrador_entry = QLineEdit()
        tmpl_layout.addWidget(self.linx_url_integrador_entry)

        scroll_layout.addWidget(tmpl_group)

        # Services Section
        srv_group = QGroupBox("Nomes dos Serviços Windows (Linx)")
        srv_layout = QGridLayout(srv_group)

        srv_layout.addWidget(QLabel("Serviço DFe:"), 0, 0)
        self.linx_service_dfe_entry = QLineEdit("DFeServico")
        srv_layout.addWidget(self.linx_service_dfe_entry, 0, 1)

        srv_layout.addWidget(QLabel("Serviço DataSnap:"), 0, 2)
        self.linx_service_datasnap_entry = QLineEdit("RedirecionaDatasnap")
        srv_layout.addWidget(self.linx_service_datasnap_entry, 0, 3)

        srv_layout.addWidget(QLabel("Serviço 3Camadas:"), 1, 0)
        self.linx_service_3camadas_entry = QLineEdit("VerificaServer3Camadas")
        srv_layout.addWidget(self.linx_service_3camadas_entry, 1, 1)

        srv_layout.addWidget(QLabel("Serviço Integrador:"), 1, 2)
        self.linx_service_integrador_entry = QLineEdit("dmLDIServer")
        srv_layout.addWidget(self.linx_service_integrador_entry, 1, 3)

        srv_layout.addWidget(QLabel("Encerrar Processos (Pattern):"), 2, 0)
        self.linx_kill_pattern_entry = QLineEdit("wsContabil")
        srv_layout.addWidget(self.linx_kill_pattern_entry, 2, 1, 1, 3)

        scroll_layout.addWidget(srv_group)

        # Target Paths Section
        paths_group = QGroupBox("Diretórios de Destino Locais (Linx)")
        paths_layout = QVBoxLayout(paths_group)

        p1_row = QHBoxLayout()
        p1_row.addWidget(QLabel("Apollo/Atualiza:"))
        self.linx_path_normal_entry = QLineEdit()
        p1_row.addWidget(self.linx_path_normal_entry, 1)
        paths_layout.addLayout(p1_row)

        p2_row = QHBoxLayout()
        p2_row.addWidget(QLabel("3Camadas Server:"))
        self.linx_path_server_entry = QLineEdit()
        p2_row.addWidget(self.linx_path_server_entry, 1)
        paths_layout.addLayout(p2_row)

        p3_row = QHBoxLayout()
        p3_row.addWidget(QLabel("3Camadas Client:"))
        self.linx_path_client_entry = QLineEdit()
        p3_row.addWidget(self.linx_path_client_entry, 1)
        paths_layout.addLayout(p3_row)

        scroll_layout.addWidget(paths_group)

        layout.addWidget(scroll, 1)

        btn_save = QPushButton("Salvar Configurações Linx")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 12px; font-size: 14px;")
        btn_save.clicked.connect(self.save_settings_manually)
        layout.addWidget(btn_save)

    def setup_tab_linx_about(self):
        tab = self.frame_linx_about
        layout = QVBoxLayout(tab)

        info_group = QGroupBox("Informações do Desenvolvedor e Versão (Linx DMS)")
        info_layout = QVBoxLayout(info_group)
        details_text = (
            "Desenvolvedor: Robson Santos\n"
            "Contato: robsonshk@gmail.com\n"
            "Versão do Programa: 2.0.0\n"
            "Finalidade: Facilitar o download, descompactação, aplicação de atualizações e limpeza de arquivos do sistema Linx DMS."
        )
        lbl_info = QLabel(details_text)
        lbl_info.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(lbl_info)
        layout.addWidget(info_group)

        lic_group = QGroupBox("🔒 Status do Licenciamento")
        lic_layout = QVBoxLayout(lic_group)

        lm = LicenseManager(app_name="AtualizadorSistemas")
        lic = lm.load_license()

        status_str = "🟢 Licença Ativa e Válida" if lic.get("is_valid") else "🔴 Licença Inativa / Não Validada"
        empresa_str = lic.get("company_name", "Não informada")
        validade_str = lic.get("valid_until", "Indefinida")
        hwid_str = get_hwid()

        self.lbl_linx_lic_status = QLabel(f"Status: {status_str}")
        self.lbl_linx_lic_status.setStyleSheet("font-weight: bold;")
        self.lbl_linx_lic_company = QLabel(f"Empresa: {empresa_str}")
        self.lbl_linx_lic_validity = QLabel(f"Validade: {validade_str}")
        self.lbl_linx_lic_hwid = QLabel(f"Hardware ID (HWID): {hwid_str}")
        self.lbl_linx_lic_hwid.setStyleSheet("font-family: monospace; font-size: 10px; color: #aaa;")

        btn_manage_lic = QPushButton("Gerenciar / Reativar Licença")
        btn_manage_lic.setStyleSheet("padding: 6px; font-weight: bold;")
        btn_manage_lic.clicked.connect(self.open_license_manager)

        lic_layout.addWidget(self.lbl_linx_lic_status)
        lic_layout.addWidget(self.lbl_linx_lic_company)
        lic_layout.addWidget(self.lbl_linx_lic_validity)
        lic_layout.addWidget(self.lbl_linx_lic_hwid)
        lic_layout.addWidget(btn_manage_lic)

        layout.addWidget(lic_group)

        change_group = QGroupBox("Histórico de Alterações do Linx (Changelog)")
        change_layout = QVBoxLayout(change_group)
        txt_change = QTextEdit()
        txt_change.setReadOnly(True)
        txt_change.setText(CHANGELOG_APOLLO)
        change_layout.addWidget(txt_change)
        layout.addWidget(change_group, 1)

    def setup_tab_linx_notes(self):
        tab = self.frame_linx_notes
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        lbl_title = QLabel("📝 Observações e Anotações da Máquina / Cliente (Linx DMS)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        lbl_subtitle = QLabel("Espaço livre para salvar anotações pertinentes à configuração desta máquina, IP de banco, particularidades, etc.")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)

        self.linx_notes_box = QTextEdit()
        self.linx_notes_box.setReadOnly(False)
        self.linx_notes_box.setPlaceholderText("Digite aqui suas observações sobre esta máquina ou cliente (Linx DMS)...")
        self.linx_notes_box.setStyleSheet("font-family: sans-serif; font-size: 13px; background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; padding: 8px;")

        initial_notes = getattr(self, "app_config", {}).get("linx_notes", "")
        if initial_notes:
            self.linx_notes_box.setPlainText(initial_notes)

        layout.addWidget(self.linx_notes_box, 1)

        footer_layout = QHBoxLayout()
        self.linx_notes_status_lbl = QLabel("")
        self.linx_notes_status_lbl.setStyleSheet("font-size: 12px; color: #a6e3a1; font-weight: bold;")
        footer_layout.addWidget(self.linx_notes_status_lbl, 1)

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
        btn_save.clicked.connect(self.save_linx_notes)
        footer_layout.addWidget(btn_save)

        layout.addLayout(footer_layout)

    def save_linx_notes(self):
        if hasattr(self, "linx_notes_box"):
            notes_text = self.linx_notes_box.toPlainText()
            self.app_config["linx_notes"] = notes_text
            if config.save_config(self.app_config):
                now_str = datetime.now().strftime("%H:%M:%S")
                if hasattr(self, "linx_notes_status_lbl"):
                    self.linx_notes_status_lbl.setText(f"✓ Observações salvas às {now_str}")
                QMessageBox.information(self, "Sucesso", "Observações salvas com sucesso!")
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível salvar as observações no arquivo de configuração.")


    # ----------------- APOLLO THREAD LOGIC -----------------
    def log_linx_dl(self, msg):
        formatted = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(formatted, flush=True)
        if hasattr(self, "linx_dl_log_signal"):
            self.linx_dl_log_signal.emit(formatted)
        elif hasattr(self, "linx_dl_log_box"):
            self.log_linx_dl_ui(formatted)

    def log_linx_dl_ui(self, formatted):
        if hasattr(self, "linx_dl_log_box"):
            self.linx_dl_log_box.append(formatted)
            self.linx_dl_log_box.verticalScrollBar().setValue(self.linx_dl_log_box.verticalScrollBar().maximum())

    def status_linx_dl(self, msg):
        if hasattr(self, "linx_dl_status_signal"):
            self.linx_dl_status_signal.emit(msg)
        elif hasattr(self, "linx_dl_status_label"):
            self.status_linx_dl_ui(msg)

    def status_linx_dl_ui(self, msg):
        if hasattr(self, "linx_dl_status_label"):
            self.linx_dl_status_label.setText(msg)

    def progress_linx_dl(self, val):
        if hasattr(self, "linx_dl_progress_signal"):
            self.linx_dl_progress_signal.emit(int(val))
        elif hasattr(self, "linx_dl_progressbar"):
            self.progress_linx_dl_ui(int(val))

    def progress_linx_dl_ui(self, val):
        if hasattr(self, "linx_dl_progressbar"):
            self.linx_dl_progressbar.setValue(int(val))

    def on_linx_download_finished(self, success: bool, message: str):
        if hasattr(self, "btn_run_linx_download"):
            self.btn_run_linx_download.setEnabled(True)
        if hasattr(self, "btn_pause_linx_download"):
            self.btn_pause_linx_download.setEnabled(False)
            self.btn_pause_linx_download.setText("Pausar")
        if hasattr(self, "btn_cancel_linx_download"):
            self.btn_cancel_linx_download.setEnabled(False)

        if success:
            QMessageBox.information(self, "Sucesso", message)
        else:
            QMessageBox.warning(self, "Download Finalizado", message)

    def run_linx_download(self):
        c = getattr(self, "app_config", {})
        version = self.linx_version_entry.text().strip() if hasattr(self, "linx_version_entry") else ""
        path = self.linx_path_entry.text().strip() if hasattr(self, "linx_path_entry") else ""

        if not path:
            default_p = "C:\\atualizacao" if getattr(self, "os_type", "Windows") == "Windows" else "./AtualizacaoLinx"
            path = c.get("linx_download_path_win" if getattr(self, "os_type", "Windows") == "Windows" else "linx_download_path_linux", default_p)
            if not path:
                path = default_p
            if hasattr(self, "linx_path_entry"):
                self.linx_path_entry.setText(path)

        if not version:
            version = "5.19"
            if hasattr(self, "linx_version_entry"):
                self.linx_version_entry.setText(version)

        self.save_ui_to_config()
        self.linx_download_paused = False
        self.linx_download_cancelled = False
        self.btn_run_linx_download.setEnabled(False)
        self.btn_pause_linx_download.setEnabled(True)
        self.btn_cancel_linx_download.setEnabled(True)
        self.linx_dl_log_box.clear()
        self.linx_dl_progressbar.setValue(0)
        self.status_linx_dl("Iniciando download do Linx...")

        threading.Thread(target=self._linx_download_thread, daemon=True).start()

    def toggle_linx_pause_download(self):
        if getattr(self, "linx_download_paused", False):
            self.linx_download_paused = False
            self.btn_pause_linx_download.setText("Pausar")
            self.log_linx_dl("Processo retomado.")
            self.status_linx_dl("Retomando download...")
        else:
            self.linx_download_paused = True
            self.btn_pause_linx_download.setText("Retomar")
            self.log_linx_dl("Processo pausado. Aguardando...")
            self.status_linx_dl("Pausado.")

    def cancel_linx_download(self):
        self.linx_download_cancelled = True
        self.linx_download_paused = False
        self.log_linx_dl("Solicitação de cancelamento enviada. Aguardando...")
        self.status_linx_dl("Cancelando...")

    def _linx_download_thread(self):
        log = self.log_linx_dl
        status = self.status_linx_dl

        def check_pause_cancel():
            while getattr(self, "linx_download_paused", False):
                time.sleep(0.1)
                if getattr(self, "linx_download_cancelled", False):
                    raise Exception("Processo cancelado pelo usuário.")
            if getattr(self, "linx_download_cancelled", False):
                raise Exception("Processo cancelado pelo usuário.")

        try:
            c = self.app_config
            package = self.linx_package_menu.currentText().strip()
            version = self.linx_version_entry.text().strip()
            path = self.linx_path_entry.text().strip()

            if not version or not path:
                log("Erro: Versão e pasta de destino são obrigatórias.")
                status("Erro: preencha os parâmetros.")
                if hasattr(self, "linx_dl_finished_signal"):
                    self.linx_dl_finished_signal.emit(False, "Preencha a versão e a pasta de destino.")
                return

            version_with_v = version if version.lower().startswith("v") else "v" + version

            log("--- INICIANDO PROCESSO DOWNLOAD LINX ---")
            log(f"Pacote selecionado: {package}")
            log(f"Versão: {version_with_v}")
            log(f"Pasta de downloads: {os.path.abspath(path)}")
            os.makedirs(path, exist_ok=True)

            downloads_to_make = []

            # 1. Delphi (Padrão)
            if self.linx_dl_delphi_var.isChecked():
                tmpl = c.get("linx_url_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_delphi_template"]
                url = tmpl.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}.zip"
                downloads_to_make.append(("Delphi (Padrão)", url, filename))

            # 2. 3 Camadas Server
            if self.linx_dl_server_var.isChecked():
                tmpl = c.get("linx_url_server_template", "").strip() or config.DEFAULT_CONFIG["linx_url_server_template"]
                url = tmpl.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}_3Camadas_Server.zip"
                downloads_to_make.append(("3 Camadas Server", url, filename))

            # 3. 3 Camadas Client
            if self.linx_dl_client_var.isChecked():
                tmpl = c.get("linx_url_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_client_template"]
                url = tmpl.replace("{package}", package).replace("{version}", version_with_v)
                filename = f"DVI_Pacote_Evolutivo_{package}_{version_with_v}_3Camadas_Client.zip"
                downloads_to_make.append(("3 Camadas Client", url, filename))

            # 4. Instalador Web
            if self.linx_dl_web_var.isChecked():
                tmpl = c.get("linx_url_web_template", "").strip() or config.DEFAULT_CONFIG["linx_url_web_template"]
                url = tmpl.replace("{package}", package).replace("{version}", version_with_v)
                filename = "LinxDMS.zip"
                downloads_to_make.append(("Instalador Web", url, filename))

            # 5. Linx Integrador
            if self.linx_dl_integrador_var.isChecked():
                tmpl = c.get("linx_url_integrador_template", "").strip() or config.DEFAULT_CONFIG["linx_url_integrador_template"]
                url = tmpl.replace("{package}", package).replace("{version}", version_with_v)
                filename = "LinxDMSIntegrador.zip"
                downloads_to_make.append(("Linx DMS Integrador", url, filename))

            # 6. Comissões
            if self.linx_dl_comissoes_var.isChecked():
                if self.linx_dl_delphi_var.isChecked():
                    tmpl = c.get("linx_url_comissoes_delphi_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_delphi_template"]
                    url = tmpl.replace("{version}", version_with_v)
                    downloads_to_make.append(("Comissões Delphi", url, "LinxDMSComissoes.zip"))
                if self.linx_dl_client_var.isChecked():
                    tmpl = c.get("linx_url_comissoes_client_template", "").strip() or config.DEFAULT_CONFIG["linx_url_comissoes_client_template"]
                    url = tmpl.replace("{version}", version_with_v)
                    downloads_to_make.append(("Comissões Client", url, "LinxDMSComissoesClient.zip"))
                if self.linx_dl_server_var.isChecked():
                    log("Aviso: Comissões não possui pacote de Server. Ignorando download Server para Comissões.")

            # 7. Apoio
            apoio_modules = []
            if self.linx_dl_apoio_trocafornec_var.isChecked():
                apoio_modules.append(("Troca Fornecedor", "TrocaFornec"))
            if self.linx_dl_apoio_trocaserie_var.isChecked():
                apoio_modules.append(("Troca Série Transmissão", "TrocaSerieTran"))
            if self.linx_dl_apoio_verificadiaria_var.isChecked():
                apoio_modules.append(("Verifica Composição Diária", "VerificaComposicaoDiaria"))

            for label, base_filename in apoio_modules:
                tmpl = c.get("linx_url_apoio_template", "").strip() or config.DEFAULT_CONFIG["linx_url_apoio_template"]
                if self.linx_dl_delphi_var.isChecked():
                    url = tmpl.replace("{version}", version_with_v).replace("{filename}", base_filename)
                    downloads_to_make.append((f"{label} Delphi", url, f"{base_filename}.zip"))
                if self.linx_dl_client_var.isChecked():
                    client_filename = f"{base_filename}Client"
                    url = tmpl.replace("{version}", version_with_v).replace("{filename}", client_filename)
                    downloads_to_make.append((f"{label} Client", url, f"{client_filename}.zip"))
                if self.linx_dl_server_var.isChecked():
                    log(f"Aviso: {label} não possui pacote de Server. Ignorando download Server para {label}.")

            if not downloads_to_make:
                log("Aviso: Nenhuma opção de download válida foi selecionada.")
                status("Selecione pelo menos um pacote para download.")
                if hasattr(self, "linx_dl_finished_signal"):
                    self.linx_dl_finished_signal.emit(False, "Selecione pelo menos um pacote para download.")
                return

            total_items = len(downloads_to_make)
            for idx, (label, url, filename) in enumerate(downloads_to_make):
                check_pause_cancel()
                dest_file = os.path.join(path, filename)
                log(f"Baixando ({idx+1}/{total_items}) {label}...")
                log(f"URL: {url}")
                status(f"Baixando [{idx+1}/{total_items}]: {filename}...")

                start_t = time.time()
                last_u = 0

                def progress_cb(dl_bytes, total_bytes):
                    nonlocal last_u
                    check_pause_cancel()
                    now = time.time()
                    if now - last_u >= 0.1 or (total_bytes > 0 and dl_bytes >= total_bytes):
                        last_u = now
                        elapsed = max(now - start_t, 0.001)
                        speed = dl_bytes / elapsed
                        speed_str = f"{speed / (1024*1024):.2f} MB/s" if speed >= 1024*1024 else (f"{speed / 1024:.1f} KB/s" if speed >= 1024 else f"{speed:.0f} B/s")

                        if total_bytes > 0:
                            pct = dl_bytes / total_bytes
                            item_progress = (idx + pct) / total_items
                            self.progress_linx_dl(int(item_progress * 100))
                            self.status_linx_dl(f"Baixando {filename} - {pct*100:.1f}% ({speed_str})")

                utils.download_http_file(url, dest_file, progress_callback=progress_cb, check_pause_cancel=check_pause_cancel)
                log(f"Concluído: {filename}")

            status("Processo de download Linx finalizado com sucesso!")
            log("--- DOWNLOADS DO LINX CONCLUÍDOS COM SUCESSO ---")
            if hasattr(self, "linx_dl_finished_signal"):
                self.linx_dl_finished_signal.emit(True, "Processo de download Linx finalizado com sucesso!")

        except Exception as e:
            log(f"ERRO durante download do Linx: {e}")
            status("Erro durante o download.")
            if hasattr(self, "linx_dl_finished_signal"):
                self.linx_dl_finished_signal.emit(False, str(e))



    def log_linx_update(self, msg):
        formatted = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(formatted, flush=True)
        if hasattr(self, "linx_update_log_signal"):
            self.linx_update_log_signal.emit(formatted)
        elif hasattr(self, "linx_update_log_box"):
            self.log_linx_update_ui(formatted)

    def log_linx_update_ui(self, formatted):
        if hasattr(self, "linx_update_log_box"):
            self.linx_update_log_box.append(formatted)
            self.linx_update_log_box.verticalScrollBar().setValue(self.linx_update_log_box.verticalScrollBar().maximum())

    def status_linx_update(self, msg):
        if hasattr(self, "linx_update_status_signal"):
            self.linx_update_status_signal.emit(msg)
        elif hasattr(self, "linx_update_status_label"):
            self.status_linx_update_ui(msg)

    def status_linx_update_ui(self, msg):
        if hasattr(self, "linx_update_status_label"):
            self.linx_update_status_label.setText(msg)

    def progress_linx_update(self, val):
        if hasattr(self, "linx_update_progress_signal"):
            self.linx_update_progress_signal.emit(int(val))
        elif hasattr(self, "linx_update_progressbar"):
            self.progress_linx_update_ui(int(val))

    def progress_linx_update_ui(self, val):
        if hasattr(self, "linx_update_progressbar"):
            self.linx_update_progressbar.setValue(int(val))

    def on_linx_update_finished(self, success: bool, message: str):
        if hasattr(self, "btn_run_linx_update"):
            self.btn_run_linx_update.setEnabled(True)
        if hasattr(self, "refresh_linx_services"):
            self.refresh_linx_services()
        if success:
            QMessageBox.information(self, "Sucesso", message)
        else:
            QMessageBox.warning(self, "Atualização Finalizada", message)

    def run_linx_update(self):
        c = getattr(self, "app_config", {})
        download_dir = self.linx_path_entry.text().strip() if hasattr(self, "linx_path_entry") else ""
        if not download_dir:
            default_p = "C:\\atualizacao" if getattr(self, "os_type", "Windows") == "Windows" else "./AtualizacaoLinx"
            download_dir = c.get("linx_download_path_win" if getattr(self, "os_type", "Windows") == "Windows" else "linx_download_path_linux", default_p)
            if not download_dir:
                download_dir = default_p
            if hasattr(self, "linx_path_entry"):
                self.linx_path_entry.setText(download_dir)

        self.save_ui_to_config()
        if hasattr(self, "btn_run_linx_update"):
            self.btn_run_linx_update.setEnabled(False)
        if hasattr(self, "linx_update_log_box"):
            self.linx_update_log_box.clear()
        if hasattr(self, "linx_update_progressbar"):
            self.linx_update_progressbar.setValue(0)

        self.status_linx_update("Iniciando aplicação de atualizações...")
        threading.Thread(target=self._linx_update_thread, daemon=True).start()

    def _linx_update_thread(self):
        log = self.log_linx_update
        status = self.status_linx_update

        try:
            c = getattr(self, "app_config", {})
            download_dir = self.linx_path_entry.text().strip() if hasattr(self, "linx_path_entry") else "C:\\atualizacao"

            dest_normal = c.get("linx_path_normal_win", "C:\\Apollo\\Atualiza") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_normal_linux", "./Apollo_Atualiza")
            dest_server = c.get("linx_path_server_win", "C:\\3Camadas") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
            dest_client = c.get("linx_path_client_win", "C:\\3Camadas\\Atualiza") if getattr(self, "os_type", "Windows") == "Windows" else c.get("linx_path_client_linux", "./3Camadas_Atualiza")

            log("--- INICIANDO ATUALIZAÇÃO DO LINX DMS ---")
            log(f"Pasta de Origem (Zip): {os.path.abspath(download_dir)}")
            log(f"Destino Apollo/Atualiza (Delphi): {os.path.abspath(dest_normal)}")
            log(f"Destino 3Camadas Server: {os.path.abspath(dest_server)}")
            log(f"Destino 3Camadas Client: {os.path.abspath(dest_client)}")

            if not os.path.exists(download_dir):
                log(f"Erro: A pasta de origem '{download_dir}' não existe.")
                status("Pasta de origem não encontrada.")
                if hasattr(self, "linx_update_finished_signal"):
                    self.linx_update_finished_signal.emit(False, f"Pasta de origem não encontrada: {download_dir}")
                return

            zip_files = [f for f in os.listdir(download_dir) if f.lower().endswith(".zip")]
            total_zips = len(zip_files)

            if not zip_files:
                log(f"Aviso: Nenhum arquivo .zip encontrado na pasta '{download_dir}'.")
                status("Nenhum zip para descompactar.")
                if hasattr(self, "linx_update_finished_signal"):
                    self.linx_update_finished_signal.emit(True, "Nenhum arquivo zip para descompactar.")
                return

            log(f"Encontrados {total_zips} arquivos .zip para processar.")

            # 1. Backup automático da pasta Apollo/Atualiza (Compressão Máxima)
            if c.get("linx_backup_apollo", True):
                status("Fazendo backup do Apollo (Compressão Máxima)...")
                log("--- INICIANDO BACKUP MÁXIMO DA PASTA APOLLO/ATUALIZA ---")
                backup_zip = utils.make_apollo_backup(dest_normal, log_callback=log)
                if backup_zip:
                    c["last_apollo_backup_zip"] = backup_zip
                    config.save_config(c)

            # 2. Descompactação dos pacotes direcionada por tipo
            errors_occurred = []

            for idx, zf in enumerate(zip_files):
                full_zip = os.path.join(download_dir, zf)
                name_lower = zf.lower()

                # Verifica se o arquivo é um pacote de instalação (LinxDMS Web ou Linx DMS Integrador)
                is_linx_web = (name_lower == "linxdms.zip") or ("linxdms" in name_lower and not any(k in name_lower for k in ["comissoes", "apoio", "evolutivo", "3camadas"]))
                is_integrador = ("linxdmsintegrador" in name_lower) or ("integrador" in name_lower)

                if is_linx_web or is_integrador:
                    pkg_label = "Instalador Web (LinxDMS)" if is_linx_web else "Linx DMS Integrador"
                    status(f"Processando {pkg_label} [{idx+1}/{total_zips}]...")
                    log(f"\n[{idx+1}/{total_zips}] Processando: {zf} ({pkg_label}) via pasta temporária...")

                    temp_extract = os.path.join(download_dir, f"temp_extract_{os.path.splitext(zf)[0]}")
                    try:
                        # Extrai para pasta temporária
                        utils.unzip_file(full_zip, temp_extract, log_callback=log)

                        # Busca por instaladores .exe ou .msi dentro da pasta temporária
                        installers = []
                        for root, dirs, files in os.walk(temp_extract):
                            for f in files:
                                if f.lower().endswith(".msi") or f.lower().endswith(".exe"):
                                    installers.append(os.path.join(root, f))

                        if installers:
                            inst_path = installers[0]
                            inst_name = os.path.basename(inst_path)
                            log(f"Instalador encontrado: '{inst_name}'. Executando como Administrador...")
                            status(f"Executando {inst_name}...")
                            success = utils.execute_script_as_admin(inst_path, log_callback=log)
                            if success:
                                log(f"Instalação de '{inst_name}' finalizada com sucesso.")
                            else:
                                log(f"Aviso: Falha ou encerramento na execução do instalador '{inst_name}'.")
                        else:
                            log(f"Nenhum instalador (.exe ou .msi) encontrado em '{zf}'. Copiando conteúdo para {dest_normal}...")
                            import shutil
                            for item in os.listdir(temp_extract):
                                s = os.path.join(temp_extract, item)
                                d = os.path.join(dest_normal, item)
                                if os.path.isdir(s):
                                    shutil.copytree(s, d, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(s, d)

                    except Exception as inst_err:
                        err_msg = f"Falha ao processar instalador {zf}: {inst_err}"
                        log(err_msg)
                        errors_occurred.append(err_msg)
                    finally:
                        if os.path.exists(temp_extract):
                            try:
                                import shutil
                                shutil.rmtree(temp_extract, ignore_errors=True)
                                log("Pasta temporária de extração limpa com sucesso.")
                            except Exception as rm_err:
                                log(f"Aviso ao remover pasta temporária: {rm_err}")
                else:
                    # Roteamento dos pacotes normais de atualização
                    if "3camadas_server" in name_lower or "_server.zip" in name_lower or "server_3camadas" in name_lower:
                        target_dir = dest_server
                        pkg_type = "3Camadas Server"
                    elif "3camadas_client" in name_lower or "_client.zip" in name_lower or "client_3camadas" in name_lower or name_lower.endswith("client.zip"):
                        target_dir = dest_client
                        pkg_type = "3Camadas Client"
                    else:
                        target_dir = dest_normal
                        pkg_type = "Delphi (Apollo/Atualiza)"

                    status(f"Descompactando [{idx+1}/{total_zips}]: {zf}...")
                    log(f"\n[{idx+1}/{total_zips}] Processando: {zf} ({pkg_type}) -> {target_dir}")

                    try:
                        utils.unzip_file(full_zip, target_dir, log_callback=log)
                    except Exception as extract_err:
                        err_msg = f"Falha ao descompactar {zf}: {extract_err}"
                        errors_occurred.append(err_msg)

                self.progress_linx_update(int(((idx + 1) / total_zips) * 100))


            # 3. Exclusão dos arquivos .zip baixados na pasta de origem após a descompactação
            log("\n--- EXCLUINDO ARQUIVOS ZIP BAIXADOS DA PASTA DE ORIGEM ---")
            deleted_zips_count = 0
            for zf in zip_files:
                full_zip = os.path.join(download_dir, zf)
                try:
                    if os.path.exists(full_zip):
                        os.remove(full_zip)
                        log(f"Arquivo zip excluído: {zf}")
                        deleted_zips_count += 1
                except Exception as del_err:
                    log(f"Aviso ao excluir arquivo zip '{zf}': {del_err}")

            if deleted_zips_count > 0:
                log(f"Limpeza concluída: {deleted_zips_count} arquivo(s) .zip excluído(s) da pasta '{download_dir}'.")

            if errors_occurred:
                status("Atualização concluída com avisos de permissão.")
                log("\n--- RESUMO DE AVISOS DE PERMISSÃO / ERROS ---")
                for err in errors_occurred:
                    log(f"• {err}")
                if hasattr(self, "linx_update_finished_signal"):
                    self.linx_update_finished_signal.emit(False, "Alguns arquivos não puderam ser descompactados devido a permissões/processos em execução:\n\n" + "\n".join(errors_occurred[:3]))
            else:
                status("Atualização do Linx concluída com sucesso!")
                log("\n--- ATUALIZAÇÃO DO LINX CONCLUÍDA COM SUCESSO ---")
                if hasattr(self, "linx_update_finished_signal"):
                    self.linx_update_finished_signal.emit(True, "Atualização do Linx concluída com sucesso!")


        except Exception as e:
            log(f"ERRO durante atualização do Linx: {e}")
            status("Erro na atualização.")
            if hasattr(self, "linx_update_finished_signal"):
                self.linx_update_finished_signal.emit(False, str(e))


        finally:
            QTimer.singleShot(0, lambda: self.btn_run_linx_update.setEnabled(True))

    def open_linx_folder(self, target):
        c = self.app_config
        if target == "apollo":
            path = c.get("linx_path_normal_win", "C:\\Apollo") if self.os_type == "Windows" else "./Apollo"
        else:
            path = c.get("linx_path_server_win", "C:\\3camadas") if self.os_type == "Windows" else "./3Camadas"

        os.makedirs(path, exist_ok=True)
        if self.os_type == "Windows":
            os.startfile(path)
        else:
            import subprocess
            subprocess.run(["xdg-open", path])
