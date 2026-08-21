import os
import sys
import re
import platform
import threading
import time
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QScrollArea, QWidget,
    QTextEdit, QMessageBox, QFrame, QGroupBox
)

import config
import ftp_client
import utils


class CTkToolTip:
    """Helper compatível para definir tooltips em widgets PySide6."""
    def __init__(self, widget, text, delay=300):
        if widget is not None and text:
            widget.setToolTip(text)


class ExtensionCleanupDialog(QDialog):
    """Pop-up modal em PySide6 para pesquisa e exclusão de arquivos por Regex, Glob ou Extensão."""
    def __init__(self, parent_app, system_name="nbs"):
        super().__init__(parent_app)
        self.app = parent_app
        self.system_name = system_name
        self.app_config = parent_app.app_config if hasattr(parent_app, "app_config") else config.load_config()
        self.os_type = platform.system()

        sys_title = "NBS" if system_name == "nbs" else "Linx DMS / Apollo"
        self.setWindowTitle(f"Limpeza de Arquivos por Regex / Extensão - {sys_title}")
        self.resize(720, 560)
        self.setModal(True)

        self.all_files_found = []
        self.checkboxes = {}
        self.custom_path = ""

        self._build_ui()
        self.scan_directory()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        sys_title = "NBS" if self.system_name == "nbs" else "Linx DMS / Apollo"
        title_lbl = QLabel(f"🧹 Utilitário de Limpeza de Arquivos por Regex / Extensão ({sys_title})")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title_lbl)

        ctrl_group = QGroupBox("Configurações do Diretório e Filtros")
        ctrl_layout = QVBoxLayout(ctrl_group)

        # Folder Selection Row
        folder_row = QHBoxLayout()
        folder_lbl = QLabel("Pasta a Limpar:")
        folder_lbl.setStyleSheet("font-weight: bold;")

        if self.system_name == "nbs":
            menu_values = ["C:\\NBS", "C:\\Atualizacao", "Outro Diretório..."]
        else:
            menu_values = ["C:\\Apollo", "C:\\3camadas", "C:\\atualizacao", "Outro Diretório..."]

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(menu_values)
        self.dir_combo.currentTextChanged.connect(self.on_dir_combo_changed)

        btn_browse = QPushButton("📁 Selecionar Pasta...")
        btn_browse.setStyleSheet("font-weight: bold;")
        btn_browse.clicked.connect(self.browse_custom_dir)

        folder_row.addWidget(folder_lbl)
        folder_row.addWidget(self.dir_combo, 1)
        folder_row.addWidget(btn_browse)
        ctrl_layout.addLayout(folder_row)

        self.dir_label_path = QLabel("Caminho Ativo: -")
        self.dir_label_path.setStyleSheet("font-size: 11px; font-style: italic; color: #a6adc8;")
        ctrl_layout.addWidget(self.dir_label_path)

        # Extension Filter Row
        ext_row = QHBoxLayout()
        ext_lbl = QLabel("Extensão:")
        ext_lbl.setStyleSheet("font-weight: bold;")
        self.ext_entry = QLineEdit(".*")
        self.ext_entry.setPlaceholderText("Ex: .exe, .dll, .log, .tmp ou .* para todos")
        self.ext_entry.returnPressed.connect(self.scan_directory)

        btn_search = QPushButton("🔍 Varrer Pasta")
        btn_search.setStyleSheet("font-weight: bold; background-color: #313244; color: #cdd6f4;")
        btn_search.clicked.connect(self.scan_directory)

        ext_row.addWidget(ext_lbl)
        ext_row.addWidget(self.ext_entry, 1)
        ext_row.addWidget(btn_search)
        ctrl_layout.addLayout(ext_row)

        # Regex / Glob Filter Row
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Filtro Regex / Glob:")
        filter_lbl.setStyleSheet("font-weight: bold;")
        self.filter_entry = QLineEdit()
        self.filter_entry.setPlaceholderText(r"Ex Regex: ^.*2026.*$, ^NBS_.*\.exe$, .*\.(tmp|log)$")

        self.filter_entry.textChanged.connect(self.populate_list)

        btn_clear = QPushButton("Limpar Filtro")
        btn_clear.clicked.connect(self._clear_filter)

        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self.filter_entry, 1)
        filter_row.addWidget(btn_clear)
        ctrl_layout.addLayout(filter_row)

        layout.addWidget(ctrl_group)

        # Scroll Area for File List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #181825; border: 1px solid #45475a;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)

        # Selection Action Buttons
        sel_row = QHBoxLayout()
        btn_check_all = QPushButton("☑️ Marcar Filtrados")
        btn_check_all.clicked.connect(lambda: self.select_filtered(True))
        btn_uncheck_all = QPushButton("☐ Desmarcar Filtrados")
        btn_uncheck_all.clicked.connect(lambda: self.select_filtered(False))
        sel_row.addWidget(btn_check_all)
        sel_row.addWidget(btn_uncheck_all)
        layout.addLayout(sel_row)

        # Footer Buttons
        footer = QHBoxLayout()
        btn_delete = QPushButton("🗑️ Excluir Selecionados")
        btn_delete.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 8px 16px; font-size: 13px; border-radius: 4px;")
        btn_delete.clicked.connect(self.on_delete_clicked)

        btn_close = QPushButton("Fechar")
        btn_close.setStyleSheet("padding: 8px 16px; font-size: 13px;")
        btn_close.clicked.connect(self.accept)

        footer.addWidget(btn_delete)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def on_dir_combo_changed(self, text):
        if text == "Outro Diretório...":
            self.browse_custom_dir()
        else:
            self.scan_directory()

    def get_resolved_path(self):
        dir_key = self.dir_combo.currentText()
        c = self.app_config
        if self.system_name == "nbs":
            if dir_key == "C:\\NBS":
                return c.get("nbs_path_win", "C:\\NBS") if self.os_type == "Windows" else c.get("nbs_path_linux", "./NBS_Local")
            elif dir_key == "C:\\Atualizacao":
                return c.get("nbs_download_path_win", "C:\\Atualizacao") if self.os_type == "Windows" else c.get("nbs_download_path_linux", "./Atualizacao")
        else:
            if dir_key == "C:\\Apollo":
                return c.get("linx_path_normal_win", "C:\\Apollo") if self.os_type == "Windows" else c.get("linx_path_normal_linux", "./Apollo")
            elif dir_key == "C:\\3camadas":
                return c.get("linx_path_server_win", "C:\\3camadas") if self.os_type == "Windows" else c.get("linx_path_server_linux", "./3Camadas")
            elif dir_key == "C:\\atualizacao":
                return c.get("linx_download_path_win", "C:\\atualizacao") if self.os_type == "Windows" else c.get("linx_download_path_linux", "./atualizacao")

        if dir_key == "Outro Diretório...":
            return self.custom_path
        return ""

    def browse_custom_dir(self):
        from PySide6.QtWidgets import QFileDialog
        selected = QFileDialog.getExistingDirectory(self, "Selecionar pasta para limpeza")
        if selected:
            self.custom_path = selected
            if self.dir_combo.findText("Outro Diretório...") != -1:
                self.dir_combo.setCurrentText("Outro Diretório...")
            self.scan_directory()

    def _clear_filter(self):
        self.filter_entry.clear()
        self.populate_list()

    def matches_pattern(self, filename, pattern):
        if not pattern:
            return True
        pattern = pattern.strip()
        # 1. Regex matching
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            if regex.search(filename):
                return True
        except Exception:
            pass
        # 2. Glob matching (contains * or ?)
        if "*" in pattern or "?" in pattern:
            try:
                import fnmatch
                if fnmatch.fnmatchcase(filename.lower(), pattern.lower()):
                    return True
            except Exception:
                pass
        # 3. Substring fallback
        return pattern.lower() in filename.lower()

    def scan_directory(self):
        self.all_files_found.clear()
        target_path = self.get_resolved_path()

        ext_str = self.ext_entry.text().strip().lower()
        if ext_str in ["", "*", ".*", "*.*"]:
            filter_by_ext = False
        else:
            filter_by_ext = True
            if not ext_str.startswith("."):
                ext_str = "." + ext_str

        if os.path.exists(target_path):
            try:
                for name in os.listdir(target_path):
                    if os.path.isfile(os.path.join(target_path, name)):
                        if not filter_by_ext or name.lower().endswith(ext_str):
                            self.all_files_found.append(name)
                self.all_files_found.sort()
            except Exception as e:
                print(f"Erro ao escanear diretório: {e}")

        self.populate_list()

    def populate_list(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.checkboxes.clear()
        target_path = self.get_resolved_path()
        self.dir_label_path.setText(f"Diretório ativo: {os.path.abspath(target_path) if target_path else '-'}")

        if not os.path.exists(target_path):
            lbl = QLabel("Caminho do diretório não encontrado no sistema.")
            lbl.setStyleSheet("font-style: italic; color: #f38ba8;")
            self.scroll_layout.addWidget(lbl)
            return

        filter_text = self.filter_entry.text().strip()
        filtered_files = [f for f in self.all_files_found if self.matches_pattern(f, filter_text)]

        if not filtered_files:
            lbl = QLabel("Nenhum arquivo atende ao filtro/extensão especificado.")
            lbl.setStyleSheet("font-style: italic; color: #a6adc8;")
            self.scroll_layout.addWidget(lbl)
            return

        for filename in filtered_files:
            full_path = os.path.join(target_path, filename)
            try:
                stats = os.stat(full_path)
                size_mb = stats.st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
                details = f" ({size_mb:.2f} MB) - {mtime}"
            except Exception:
                details = ""

            chk = QCheckBox(f"{filename}{details}")
            chk.setStyleSheet("color: #cdd6f4; font-size: 12px;")
            self.scroll_layout.addWidget(chk)
            self.checkboxes[full_path] = chk

    def select_filtered(self, state):
        for chk in self.checkboxes.values():
            chk.setChecked(state)

    def on_delete_clicked(self):
        to_delete = [path for path, chk in self.checkboxes.items() if chk.isChecked()]
        if not to_delete:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo selecionado para exclusão.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmação de Exclusão",
            f"Deseja realmente excluir permanentemente os {len(to_delete)} arquivos selecionados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_count = 0
        error_count = 0
        for fpath in to_delete:
            try:
                os.remove(fpath)
                deleted_count += 1
            except Exception as e:
                error_count += 1
                print(f"Erro ao remover {fpath}: {e}")

        msg = f"{deleted_count} arquivo(s) excluído(s) com sucesso!"
        if error_count > 0:
            msg += f"\n{error_count} arquivo(s) não puderam ser excluídos (podem estar em uso)."

        QMessageBox.information(self, "Resultado da Exclusão", msg)
        self.scan_directory()


class RemoteRebootDialog(QDialog):

    """Pop-up modal em PySide6 para reinício remoto de servidores via PowerShell e PING."""
    def __init__(self, parent_app, system_name="nbs"):
        super().__init__(parent_app)
        self.app = parent_app
        self.system_name = system_name
        self.app_config = parent_app.app_config if hasattr(parent_app, "app_config") else config.load_config()

        sys_title = "NBS" if system_name.lower() == "nbs" else "Linx"
        self.setWindowTitle(f"Reinício de Servidores via PowerShell - {sys_title}")
        self.resize(680, 580)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        sys_title = "NBS" if self.system_name.lower() == "nbs" else "Linx"
        title_lbl = QLabel(f"Reinício Remoto de Servidor ({sys_title})")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        sub_lbl = QLabel("Envio de comando PowerShell Restart-Computer e monitoramento por PING.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #888;")

        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)

        form_group = QGroupBox("Configurações do Servidor")
        form_layout = QVBoxLayout(form_group)

        # Server Combo row
        combo_row = QHBoxLayout()
        combo_lbl = QLabel("IP / Host Salvo:")
        combo_lbl.setStyleSheet("font-weight: bold;")

        self.server_combo = QComboBox()
        self.refresh_servers_combo()

        btn_add_ip = QPushButton("+ Salvar")
        btn_add_ip.setFixedWidth(70)
        btn_add_ip.clicked.connect(self.add_ip_action)

        btn_rem_ip = QPushButton("- Remover")
        btn_rem_ip.setFixedWidth(75)
        btn_rem_ip.setStyleSheet("background-color: #c0392b; color: white;")
        btn_rem_ip.clicked.connect(self.remove_ip_action)

        combo_row.addWidget(combo_lbl)
        combo_row.addWidget(self.server_combo, 1)
        combo_row.addWidget(btn_add_ip)
        combo_row.addWidget(btn_rem_ip)
        form_layout.addLayout(combo_row)

        # Custom IP entry row
        ip_row = QHBoxLayout()
        ip_lbl = QLabel("IP / Host Limpo:")
        self.custom_server_entry = QLineEdit()
        self.custom_server_entry.setPlaceholderText("Ex: 192.168.1.100 ou SERVIDOR-02")
        self.server_combo.currentTextChanged.connect(self.update_entry_from_combo)

        self.lbl_ping_status = QLabel("DESCONHECIDO")
        self.lbl_ping_status.setFixedWidth(110)
        self.lbl_ping_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ping_status.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")

        btn_ping = QPushButton("Testar PING")
        btn_ping.setFixedWidth(90)
        btn_ping.clicked.connect(self.test_ping_action)

        ip_row.addWidget(ip_lbl)
        ip_row.addWidget(self.custom_server_entry, 1)
        ip_row.addWidget(self.lbl_ping_status)
        ip_row.addWidget(btn_ping)
        form_layout.addLayout(ip_row)

        self.update_entry_from_combo(self.server_combo.currentText())

        # Options
        self.force_chk = QCheckBox("Forçar reinício (-Force) mesmo com usuários conectados")
        self.force_chk.setChecked(True)
        form_layout.addWidget(self.force_chk)

        # Credentials
        user_row = QHBoxLayout()
        user_row.addWidget(QLabel("Usuário (Opcional):"))
        self.user_entry = QLineEdit()
        self.user_entry.setPlaceholderText("Ex: DOMINIO\\Administrador")
        user_row.addWidget(self.user_entry, 1)
        form_layout.addLayout(user_row)

        pass_row = QHBoxLayout()
        pass_row.addWidget(QLabel("Senha (Opcional):"))
        self.pass_entry = QLineEdit()
        self.pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_entry.setPlaceholderText("Senha do Usuário")
        pass_row.addWidget(self.pass_entry, 1)
        form_layout.addLayout(pass_row)

        layout.addWidget(form_group)

        # Console Log
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log_box, 1)

        # Footer Buttons
        footer = QHBoxLayout()
        self.btn_run = QPushButton("Enviar Comando de Reinício (PowerShell)")
        self.btn_run.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.execute_reboot)

        btn_close = QPushButton("Fechar")
        btn_close.setStyleSheet("padding: 10px;")
        btn_close.clicked.connect(self.accept)

        footer.addWidget(self.btn_run)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def get_saved_servers_list(self):
        c = self.app_config
        raw_list = c.get("reboot_servers", []) or c.get("servers", [])
        cleaned = []
        for item in raw_list:
            cleaned_item = utils.clean_server_address(item)
            if cleaned_item and cleaned_item not in cleaned:
                cleaned.append(cleaned_item)
        if not cleaned:
            cleaned = ["127.0.0.1"]
        return cleaned

    def refresh_servers_combo(self):
        self.server_combo.clear()
        self.server_combo.addItems(self.get_saved_servers_list())

    def update_entry_from_combo(self, text):
        clean_val = utils.clean_server_address(text)
        if clean_val:
            self.custom_server_entry.setText(clean_val)

    def append_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {msg}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def add_ip_action(self):
        c = self.app_config
        new_ip = utils.clean_server_address(self.custom_server_entry.text())
        if not new_ip:
            QMessageBox.warning(self, "Aviso", "Informe um IP ou Hostname válido para salvar.")
            return

        saved = c.get("reboot_servers", [])
        if new_ip not in [utils.clean_server_address(x) for x in saved]:
            saved.append(new_ip)
            c["reboot_servers"] = saved
            config.save_config(c)

        self.refresh_servers_combo()
        self.server_combo.setCurrentText(new_ip)
        self.append_log(f"IP/Host '{new_ip}' adicionado aos servidores salvos.")

    def remove_ip_action(self):
        c = self.app_config
        curr = utils.clean_server_address(self.server_combo.currentText())
        if not curr:
            return
        saved = [x for x in c.get("reboot_servers", []) if utils.clean_server_address(x) != curr]
        c["reboot_servers"] = saved
        config.save_config(c)

        self.refresh_servers_combo()
        self.append_log(f"IP/Host '{curr}' removido dos servidores salvos.")

    def test_ping_action(self):
        target = utils.clean_server_address(self.custom_server_entry.text())
        if not target:
            QMessageBox.warning(self, "Aviso", "Informe um IP ou Hostname válido para testar PING.")
            return

        self.lbl_ping_status.setText("TESTANDO...")
        self.lbl_ping_status.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        self.append_log(f"Enviando PING para '{target}'...")

        def do_ping():
            is_up = utils.ping_host(target, timeout_sec=2)
            def update_ping_ui():
                if is_up:
                    self.lbl_ping_status.setText("ONLINE")
                    self.lbl_ping_status.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
                    self.append_log(f"Resposta PING de '{target}': ONLINE (Sucesso)")
                else:
                    self.lbl_ping_status.setText("OFFLINE")
                    self.lbl_ping_status.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
                    self.append_log(f"Resposta PING de '{target}': OFFLINE (Sem resposta)")

            QTimer.singleShot(0, update_ping_ui)


        threading.Thread(target=do_ping, daemon=True).start()

    def execute_reboot(self):
        raw_target = self.custom_server_entry.text().strip()
        target_host = utils.clean_server_address(raw_target)

        if not target_host:
            QMessageBox.warning(self, "Aviso", "Por favor, informe o IP ou nome de servidor limpo de destino.")
            return

        force = self.force_chk.isChecked()
        user = self.user_entry.text().strip() or None
        password = self.pass_entry.text().strip() or None

        confirm_msg = (
            f"Tem certeza que deseja reiniciar o servidor '{target_host}'?\n\n"
            f"IP Sanitizado: {target_host}\n"
            f"Atenção: Se a opção -Force estiver marcada, TODOS os usuários conectados serão desconectados."
        )

        confirm = QMessageBox.question(self, "Confirmar Reinício Remoto", confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.append_log(f"Iniciando procedimento de reinício para '{target_host}'...")
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Enviando comando...")
        self.lbl_ping_status.setText("ENVIANDO...")
        self.lbl_ping_status.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")

        def run_thread():
            try:
                success = utils.restart_remote_server_powershell(
                    server_name_or_ip=target_host,
                    force=force,
                    user=user,
                    password=password,
                    log_callback=self.append_log
                )
                if not success:
                    self.lbl_ping_status.setText("FALHA")
                    self.lbl_ping_status.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
                    QMessageBox.critical(self, "Erro", f"Não foi possível enviar o comando de reinício para {target_host}.")
                    return

                self.append_log(f"Comando aceito. Monitorando reinício por PING no host '{target_host}'...")
                self.lbl_ping_status.setText("REINICIANDO...")
                self.lbl_ping_status.setStyleSheet("background-color: #d35400; color: white; font-weight: bold;")

                was_offline = False
                for _ in range(25):
                    time.sleep(2)
                    if not utils.ping_host(target_host, timeout_sec=1):
                        was_offline = True
                        self.append_log(f"Servidor '{target_host}' ficou OFFLINE (Reinício em andamento).")
                        self.lbl_ping_status.setText("OFFLINE")
                        self.lbl_ping_status.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
                        break

                self.append_log(f"Aguardando o servidor '{target_host}' retornar ONLINE...")
                is_online = False
                for _ in range(30):
                    time.sleep(3)
                    if utils.ping_host(target_host, timeout_sec=2):
                        is_online = True
                        break

                if is_online:
                    self.lbl_ping_status.setText("ONLINE")
                    self.lbl_ping_status.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
                    self.append_log(f"SUCESSO! Servidor '{target_host}' está ONLINE novamente.")
                    QMessageBox.information(self, "Reinício Confirmado", f"O servidor '{target_host}' foi reiniciado e já está ONLINE!")
                else:
                    self.lbl_ping_status.setText("AGUARDANDO...")
                    self.append_log(f"Aviso: O comando foi enviado, mas '{target_host}' ainda não respondeu ao PING.")
                    QMessageBox.information(self, "Comando Enviado", f"Comando enviado com sucesso para '{target_host}'.")
            except Exception as ex:
                self.append_log(f"Erro inesperado: {str(ex)}")
            finally:
                self.btn_run.setEnabled(True)
                self.btn_run.setText("Enviar Comando de Reinício (PowerShell)")

        threading.Thread(target=run_thread, daemon=True).start()


class CommonMixin:
    """Popups e utilitários de UI compartilhados entre NBS e Apollo."""

    def open_extension_cleanup_popup(self, system_name):
        dialog = ExtensionCleanupDialog(self, system_name=system_name)
        dialog.exec()

    def open_powershell_restart_popup(self, system_name="nbs"):
        dialog = RemoteRebootDialog(self, system_name=system_name)
        dialog.exec()
