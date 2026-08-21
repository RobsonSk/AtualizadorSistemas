import os
import sys
import json
import threading
import time
import urllib.request
import urllib.error
import hashlib
import subprocess
import platform
from cryptography.fernet import Fernet
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QGroupBox, QMessageBox
)


# 🌐 Configurações Globais do Licenciamento
DEFAULT_SERVER_URL = "https://api.licenciamento.com.br/api/validate"

# 🔓 MODO BYPASS / DESENVOLVIMENTO:
# Defina BYPASS_LICENSE = True para desativar 100% a validação de licença online.
# Ideal para ambiente de desenvolvimento local, testes sem servidor ou distribuição sem trava de licença.
BYPASS_LICENSE = False



def get_hwid() -> str:
    """Extrai o Hardware ID (HWID) único da máquina combinando UUID da Placa-Mãe e ID do Processador (SHA-256)."""
    uuid_mb = ""
    id_cpu = ""

    if platform.system() == "Windows":
        # 1. Tenta obter o UUID da placa mãe via WMIC
        try:
            cmd_mb = "wmic csproduct get uuid"
            out_mb = subprocess.check_output(cmd_mb, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")
            lines = [line.strip() for line in out_mb.splitlines() if line.strip()]
            if len(lines) >= 2 and lines[1]:
                uuid_mb = lines[1]
        except Exception:
            pass

        # 2. Tenta obter o ID do processador via WMIC
        try:
            cmd_cpu = "wmic cpu get processorid"
            out_cpu = subprocess.check_output(cmd_cpu, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")
            lines = [line.strip() for line in out_cpu.splitlines() if line.strip()]
            if len(lines) >= 2 and lines[1]:
                id_cpu = lines[1]
        except Exception:
            pass

        # 3. Fallback com PowerShell Get-CimInstance se o WMIC não retornar dados válidos
        if not uuid_mb or uuid_mb.upper() in ("UNKNOWN", "00000000-0000-0000-0000-000000000000"):
            try:
                ps_cmd = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"'
                out_ps = subprocess.check_output(ps_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore").strip()
                if out_ps:
                    uuid_mb = out_ps
            except Exception:
                pass

        if not id_cpu or id_cpu.upper() == "UNKNOWN":
            try:
                ps_cmd = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-CimInstance Win32_Processor).ProcessorId"'
                out_ps = subprocess.check_output(ps_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore").strip()
                if out_ps:
                    id_cpu = out_ps
            except Exception:
                pass

    if not uuid_mb:
        uuid_mb = "UNKNOWN_MB"
    if not id_cpu:
        id_cpu = "UNKNOWN_CPU"

    raw_str = f"MB:{uuid_mb}|CPU:{id_cpu}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class LicenseManager:
    """Gerencia a chave de criptografia única e a gravação do arquivo criptografado no AppData."""

    def __init__(self, app_name="AtualizadorSistemas"):
        appdata_dir = os.getenv("APPDATA")
        if not appdata_dir:
            appdata_dir = os.path.expanduser("~/.config")
        self.config_dir = os.path.join(appdata_dir, app_name)
        os.makedirs(self.config_dir, exist_ok=True)

        self.key_file = os.path.join(self.config_dir, "secret.key")
        self.config_file = os.path.join(self.config_dir, "license.enc")
        self.fernet = Fernet(self._get_or_create_key())

    def _get_or_create_key(self) -> bytes:
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read().strip()
                if key:
                    return key
            except Exception:
                pass
        new_key = Fernet.generate_key()
        try:
            with open(self.key_file, "wb") as f:
                f.write(new_key)
        except Exception as e:
            print(f"Erro ao salvar secret.key: {e}")
        return new_key

    def load_license(self) -> dict:
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "rb") as f:
                encrypted_data = f.read()
            if not encrypted_data:
                return {}
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode("utf-8"))
        except Exception:
            return {}

    def save_license(self, uuid_val: str, api_key: str, is_valid: bool, company_name: str = "", valid_until: str = "", hwid: str = "") -> bool:
        if not hwid:
            hwid = get_hwid()
        data = {
            "uuid": uuid_val.strip(),
            "api_key": api_key.strip(),
            "hwid": hwid.strip(),
            "is_valid": is_valid,
            "company_name": company_name,
            "valid_until": valid_until
        }
        try:
            json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            encrypted_data = self.fernet.encrypt(json_bytes)
            with open(self.config_file, "wb") as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"Erro ao salvar licença criptografada: {e}")
            return False

    def is_licensed(self) -> bool:
        lic = self.load_license()
        return bool(lic.get("api_key") and lic.get("is_valid") is True)


def validate_license_online(uuid_val: str, api_key: str, server_url: str = DEFAULT_SERVER_URL, hwid_val: str = None) -> dict:
    """Executa a requisição HTTP POST estrita para a API REST de Licenciamento enviando UUID e HWID."""
    if BYPASS_LICENSE:
        return {
            "valid": True,
            "company_name": "Bypass Temporário (Servidor Offline)",
            "valid_until": "Indefinido",
            "message": "Bypass ativo de verificação de licença."
        }

    if not uuid_val or not api_key:
        return {"valid": False, "message": "UUID ou Chave de API não informados."}

    if not hwid_val:
        hwid_val = get_hwid()

    payload = {
        "uuid": uuid_val.strip(),
        "hwid": hwid_val.strip()
    }
    json_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key.strip(),
        "User-Agent": "AtualizadorSistemas/1.0"
    }

    req = urllib.request.Request(server_url, data=json_bytes, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_bytes = response.read()
            resp_json = json.loads(resp_bytes.decode("utf-8"))

            status = resp_json.get("status")
            valid = resp_json.get("valid", False)
            resp_uuid = resp_json.get("uuid", "")
            company = resp_json.get("company_name", "")
            valid_until = resp_json.get("validUntil", "")

            # Validação Estrita conforme a especificação
            if status == "ok" and valid is True and resp_uuid.strip().lower() == uuid_val.strip().lower():
                return {
                    "valid": True,
                    "company_name": company,
                    "valid_until": valid_until,
                    "message": f"Licença Aprovada! Empresa: {company}"
                }
            else:
                msg = resp_json.get("message", "Resposta da API rejeitada ou UUID divergente.")
                return {"valid": False, "message": msg}
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("message", "Falha de Autenticação")
        except Exception:
            msg = "Falha de Autenticação"
        return {"valid": False, "message": msg}
    except urllib.error.URLError as e:
        return {"valid": False, "message": f"Erro de conexão com o servidor de licenças: {e.reason}"}
    except Exception as e:
        return {"valid": False, "message": f"Exceção ao conectar à API: {e}"}


class LicenseActivationDialog(QDialog):
    """Pop-up Modal de Ativação de Licença usando PySide6 (Qt)."""

    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.lm = license_manager
        self.result = False

        self.setWindowTitle("🔒 Ativação de Licença - Atualizador Sistemas")
        self.setFixedSize(460, 320)
        self.setModal(True)

        layout = QVBoxLayout(self)

        lbl_title = QLabel("Ativação de Licença do Sistema")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        grp_hwid = QGroupBox("Identificador do Hardware (HWID)")
        layout_hwid = QVBoxLayout(grp_hwid)
        lbl_hwid_val = QLabel(get_hwid())
        lbl_hwid_val.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold; color: #2980b9;")
        lbl_hwid_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout_hwid.addWidget(lbl_hwid_val)
        layout.addWidget(grp_hwid)

        grp_inputs = QGroupBox("Credenciais de Licenciamento")
        layout_inputs = QVBoxLayout(grp_inputs)

        lbl_uuid = QLabel("UUID do Cliente:")
        self.txt_uuid = QLineEdit()
        self.txt_uuid.setPlaceholderText("Ex: 123e4567-e89b-12d3-a456-426614174000")
        layout_inputs.addWidget(lbl_uuid)
        layout_inputs.addWidget(self.txt_uuid)

        lbl_key = QLabel("Chave de API (X-API-Key):")
        key_box = QHBoxLayout()
        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedWidth(35)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_box.addWidget(self.txt_key)
        key_box.addWidget(self.btn_toggle_key)
        layout_inputs.addWidget(lbl_key)
        layout_inputs.addLayout(key_box)

        layout.addWidget(grp_inputs)

        # Preenche se já existirem valores salvos
        lic = self.lm.load_license()
        if lic.get("uuid"):
            self.txt_uuid.setText(lic.get("uuid", ""))
        if lic.get("api_key"):
            self.txt_key.setText(lic.get("api_key", ""))

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_activate = QPushButton("Ativar Licença")
        btn_activate.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_activate.clicked.connect(self._activate)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_activate)
        layout.addLayout(btn_layout)

    def _toggle_key_visibility(self):
        if self.txt_key.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🔒")
        else:
            self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁")

    def _activate(self):
        u_val = self.txt_uuid.text().strip()
        k_val = self.txt_key.text().strip()

        if not u_val or not k_val:
            self.lbl_status.setText("Por favor, preencha o UUID e a Chave de API.")
            return

        self.lbl_status.setStyleSheet("color: #3498db; font-size: 11px;")
        self.lbl_status.setText("Validando licença online...")
        QApplication.processEvents()

        res = validate_license_online(u_val, k_val)
        if res.get("valid"):
            self.lm.save_license(
                uuid_val=u_val,
                api_key=k_val,
                is_valid=True,
                company_name=res.get("company_name", ""),
                valid_until=res.get("valid_until", "")
            )
            QMessageBox.information(
                self,
                "Licença Ativada",
                f"{res.get('message')}\n\nEmpresa: {res.get('company_name')}\nValidade: {res.get('valid_until')}"
            )
            self.accept()
        else:
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self.lbl_status.setText(res.get("message", "Falha na validação da licença."))


def enforce_license_gatekeeper(app_name="AtualizadorSistemas") -> bool:
    """
    Função Gatekeeper Principal.
    Verifica a licença online e força o modal se for inválida ou inexistente.
    Retorna True se liberado, ou False se o acesso for negado.
    """
    if BYPASS_LICENSE:
        print("[LICENSE GATEKEEPER] Modo BYPASS ATIVO: Acesso liberado sem consulta de licença.")
        return True

    lm = LicenseManager(app_name=app_name)
    lic = lm.load_license()
    u_val = lic.get("uuid", "").strip()
    k_val = lic.get("api_key", "").strip()

    # 1. Se houver licença salva, re-valida ONLINE com o servidor REST
    if u_val and k_val:
        res = validate_license_online(u_val, k_val)
        if res.get("valid"):
            lm.save_license(
                uuid_val=u_val,
                api_key=k_val,
                is_valid=True,
                company_name=res.get("company_name", ""),
                valid_until=res.get("valid_until", "")
            )
        else:
            lm.save_license(u_val, k_val, is_valid=False)

    # 2. Se a licença não for válida, abre o modal de ativação
    if not lm.is_licensed():
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        dialog = LicenseActivationDialog(lm)
        if dialog.exec() != QDialog.DialogCode.Accepted or not lm.is_licensed():
            return False

    return True


def start_background_license_checker(app_instance, app_name="AtualizadorSistemas", check_interval_seconds=900):
    """
    Inicia uma thread em segundo plano que re-valida periodicamente a licença online com o servidor REST.
    Se a licença for revogada durante o uso do programa, desativa e alerta o usuário.
    """
    def _checker_loop():
        lm = LicenseManager(app_name=app_name)
        while True:
            time.sleep(check_interval_seconds)
            try:
                lic = lm.load_license()
                u_val = lic.get("uuid", "").strip()
                k_val = lic.get("api_key", "").strip()

                if u_val and k_val:
                    res = validate_license_online(u_val, k_val)
                    if not res.get("valid"):
                        lm.save_license(u_val, k_val, is_valid=False)
                        print("[BACKGROUND LICENSE CHECK] Licença revogada ou expirada favor entrar em contato com o suporte.")
                        if hasattr(app_instance, "on_license_revoked"):
                            # Usa metaobject invoke se for QObject ou chama via signal
                            if hasattr(app_instance, "license_revoked_signal"):
                                app_instance.license_revoked_signal.emit()
                            else:
                                app_instance.on_license_revoked()
                    else:
                        lm.save_license(
                            uuid_val=u_val,
                            api_key=k_val,
                            is_valid=True,
                            company_name=res.get("company_name", ""),
                            valid_until=res.get("valid_until", "")
                        )
            except Exception as e:
                print(f"[BACKGROUND LICENSE CHECK] Erro ao checar licença: {e}")

    thread = threading.Thread(target=_checker_loop, daemon=True)
    thread.start()

