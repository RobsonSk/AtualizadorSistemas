import os
import json
import base64

CIPHER_KEY = b"NbsLinxSystemUpdaterSecretKey2026"
LEGACY_CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ftp_modules_url": "ftp://nbsi.com.br/sistemadelphi/modulos/oficiais",
    "ftp_scripts_url": "ftp://nbsi.com.br/sistemadelphi/scripts",
    "ftp_nfe_url": "ftp://nbsi.com.br/sistemadelphi/modulos/nfe",
    "ftp_interfaces_url": "ftp://nbsi.com.br/sistemadelphi/modulos/interfaces",
    "ftp_dll_url": "ftp://nbsi.com.br/sistemadelphi/modulos/dll",
    "ftp_user": "nbs",
    "ftp_password": "nbs",
    "atualizacao_path_win": "C:\\Atualizacao",
    "nbs_path_win": "C:\\NBS",
    "atualizacao_path_linux": "./Atualizacao",
    "nbs_path_linux": "./NBS_Local",
    "servers": [],
    "db_user": "nbs_db_user",
    "db_password": "nbs_db_password",
    "db_schema": "nbs_schema",
    "db_name": "NBS",
    "copy_local": True,
    "copy_servers": True,
    "download_nfe": False,
    "download_interfaces": False,
    "initial_installation": False,
    "selected_interfaces": [],
    "transition_year_enabled": False,
    "transition_year_value": "2025",
    "compress_backup": False,
    "delete_backup_after_compress": False,
    "appearance_mode": "Dark",
    "linx_package": "LINXDMS",
    "linx_version": "5.19",
    "linx_download_path_win": "C:\\atualizacao",
    "linx_download_path_linux": "./AtualizacaoLinx",
    "linx_url_delphi_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/DVI/Versoes/{version}/Pacote_Evolutivo/DVI_Pacote_Evolutivo_{package}_{version}.zip",
    "linx_url_server_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/DVI/Versoes/{version}/Pacote_Evolutivo/DVI_Pacote_Evolutivo_{package}_{version}_3Camadas_Server.zip",
    "linx_url_client_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/DVI/Versoes/{version}/Pacote_Evolutivo/DVI_Pacote_Evolutivo_{package}_{version}_3Camadas_Client.zip",
    "linx_url_web_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/linxdms/Instalador_LinxDMS/LinxDMS.zip",
    "linx_download_delphi": True,
    "linx_download_server": False,
    "linx_download_client": False,
    "linx_download_web": False,
    "linx_download_comissoes": False,
    "linx_download_apoio_trocafornec": False,
    "linx_download_apoio_trocaserie": False,
    "linx_download_apoio_verificadiaria": False,
    "linx_url_comissoes_delphi_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/DVI/Versoes/{version}/Comissoes/LinxDMSComissoes.zip",
    "linx_url_comissoes_client_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/DVI/Versoes/{version}/Comissoes/LinxDMSComissoesClient.zip",
    "linx_url_apoio_template": "https://ob-wzsp05.winov.com.br/wz01-linx01/dms/Pontuais/Apoio/{version}/{filename}.zip",
    "linx_service_dfe": "DFeServico",
    "linx_service_datasnap": "RedirecionaDatasnap",
    "linx_service_3camadas": "VerificaServer3Camadas",
    "linx_service_integrador": "dmLDIServer",
    "linx_path_normal_win": "C:\\Apollo\\Atualiza",
    "linx_path_server_win": "C:\\3Camadas",
    "linx_path_client_win": "C:\\3Camadas\\Atualiza",
    "linx_path_normal_linux": "./Apollo_Atualiza",
    "linx_path_server_linux": "./3Camadas",
    "linx_path_client_linux": "./3Camadas_Atualiza",
    "linx_download_integrador": False,
    "linx_url_integrador_template": "https://distribuicao.blob.core.windows.net/dms/DVI/LinxDMSIntegrador.zip",
    "crm_service_payara": "domain1"
}

def encrypt_data(data_str: str) -> str:
    """XOR data with key and return base64 encoded string."""
    data_bytes = data_str.encode("utf-8")
    encrypted = bytearray()
    for i in range(len(data_bytes)):
        key_byte = CIPHER_KEY[i % len(CIPHER_KEY)]
        encrypted.append(data_bytes[i] ^ key_byte)
    return base64.b64encode(encrypted).decode("utf-8")

def decrypt_data(enc_str: str) -> str:
    """Base64 decode and XOR back with key."""
    try:
        enc_bytes = base64.b64decode(enc_str.encode("utf-8"))
        decrypted = bytearray()
        for i in range(len(enc_bytes)):
            key_byte = CIPHER_KEY[i % len(CIPHER_KEY)]
            decrypted.append(enc_bytes[i] ^ key_byte)
        return decrypted.decode("utf-8")
    except Exception:
        return "{}"

def get_config_filepath():
    """Detects platform config directory and returns the config file path."""
    if os.name == "nt": # Windows
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~\\AppData\\Roaming")
        config_dir = os.path.join(appdata, "AtualizadorSistemas")
    else: # Linux / macOS
        home_config = os.environ.get("XDG_CONFIG_HOME")
        if not home_config:
            home_config = os.path.expanduser("~/.config")
        config_dir = os.path.join(home_config, "AtualizadorSistemas")
        
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.enc")

def load_config():
    """Loads configuration from config.enc, migrating legacy config.json if present."""
    config_file = get_config_filepath()
    config = {}

    # Migration check: if old plain-text config.json exists next to exe, migrate and delete it.
    if os.path.exists(LEGACY_CONFIG_FILE):
        try:
            with open(LEGACY_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Save it encrypted in the new AppData/config path
            save_config(config)
            # Remove legacy file to avoid plain text config exposure
            os.remove(LEGACY_CONFIG_FILE)
        except Exception:
            pass

    if not config:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    enc_content = f.read().strip()
                dec_content = decrypt_data(enc_content)
                config = json.loads(dec_content)
            except Exception:
                config = DEFAULT_CONFIG.copy()
        else:
            config = DEFAULT_CONFIG.copy()
            save_config(config)

    # Merge with default to ensure all keys exist
    updated = False
    fallback_keys = [
        "linx_version", "linx_download_path_win", "linx_download_path_linux",
        "linx_service_dfe", "linx_service_datasnap", "linx_service_3camadas",
        "linx_service_integrador",
        "linx_path_normal_win", "linx_path_server_win", "linx_path_client_win",
        "linx_path_normal_linux", "linx_path_server_linux", "linx_path_client_linux",
        "linx_url_integrador_template", "crm_service_payara"
    ]
    for k, v in DEFAULT_CONFIG.items():
        if k not in config or (k in fallback_keys and config[k] == ""):
            config[k] = v
            updated = True
    if updated:
        save_config(config)

    return config

def save_config(config):
    """Saves the configuration dictionary to config.enc after encrypting."""
    config_file = get_config_filepath()
    try:
        data_str = json.dumps(config, indent=4, ensure_ascii=False)
        enc_str = encrypt_data(data_str)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(enc_str)
        return True
    except Exception:
        return False
