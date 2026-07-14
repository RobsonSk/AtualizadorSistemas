import os
import json

CONFIG_FILE = "config.json"

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
    "linx_url_integrador_template": "https://distribuicao.blob.core.windows.net/dms/DVI/LinxDMSIntegrador.zip"
}

def load_config():
    """Loads configuration from config.json, merging defaults for any missing keys."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Merge with default to ensure all keys exist
                updated = False
                fallback_keys = [
                    "linx_version", "linx_download_path_win", "linx_download_path_linux",
                    "linx_service_dfe", "linx_service_datasnap", "linx_service_3camadas",
                    "linx_service_integrador",
                    "linx_path_normal_win", "linx_path_server_win", "linx_path_client_win",
                    "linx_path_normal_linux", "linx_path_server_linux", "linx_path_client_linux",
                    "linx_url_integrador_template"
                ]
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config or (k in fallback_keys and config[k] == ""):
                        config[k] = v
                        updated = True
                if updated:
                    save_config(config)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Saves the configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False
