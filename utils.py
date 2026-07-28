import os
import re
import shutil
import time
import platform
import hashlib
from datetime import datetime

def get_last_update_date(atualiza_path):
    """
    Identifies the date of the last update by looking at folders in format ddMMyyyy.
    Skips the latest folder (today's update) and returns the penultimate folder's date.
    If no other folders exist, returns None.
    """
    if not os.path.exists(atualiza_path):
        return None
        
    pattern = re.compile(r'^\d{8}$')
    subdirs = []
    
    try:
        for name in os.listdir(atualiza_path):
            full_path = os.path.join(atualiza_path, name)
            if os.path.isdir(full_path) and pattern.match(name):
                try:
                    dt = datetime.strptime(name, "%d%m%Y")
                    subdirs.append((name, dt))
                except ValueError:
                    continue
    except Exception:
        return None
        
    if not subdirs:
        return None
        
    # Sort descending by date
    subdirs.sort(key=lambda x: x[1], reverse=True)
    
    # Check if the latest folder is today
    today_str = datetime.now().strftime("%d%m%Y")
    if subdirs[0][0] == today_str:
        # Skip today's folder and return the previous one
        if len(subdirs) > 1:
            return subdirs[1][1]
        else:
            return None
    else:
        # Today's folder does not exist, so the latest folder is the last update
        return subdirs[0][1]

def backup_local_executables(nbs_path, backup_path, log_callback=None):
    """
    Copies all *.exe files from nbs_path directly into backup_path (non-recursive).
    """
    if not os.path.exists(nbs_path):
        if log_callback:
            log_callback(f"Caminho do NBS não encontrado: {nbs_path}. Ignorando backup.")
        return False
        
    os.makedirs(backup_path, exist_ok=True)
    
    copied_count = 0
    try:
        for name in os.listdir(nbs_path):
            full_path = os.path.join(nbs_path, name)
            if os.path.isfile(full_path) and name.lower().endswith(".exe"):
                dest_file = os.path.join(backup_path, name)
                if log_callback:
                    log_callback(f"Fazendo backup: {name} -> backup/")
                shutil.copy2(full_path, dest_file)
                copied_count += 1
        
        if log_callback:
            log_callback(f"Backup concluído. {copied_count} executáveis copiados para {backup_path}")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Erro durante backup dos executáveis: {str(e)}")
        return False

def backup_apollo_executables_and_dlls(apollo_path, backup_path, log_callback=None):
    r"""
    Copies all *.exe and *.dll files from apollo_path (C:\Apollo\atualiza) directly into backup_path (non-recursive).
    """
    if not os.path.exists(apollo_path):
        if log_callback:
            log_callback(f"Caminho do Apollo não encontrado: {apollo_path}. Ignorando backup.")
        return False
        
    os.makedirs(backup_path, exist_ok=True)
    
    copied_count = 0
    try:
        for name in os.listdir(apollo_path):
            full_path = os.path.join(apollo_path, name)
            if os.path.isfile(full_path) and (name.lower().endswith(".exe") or name.lower().endswith(".dll")):
                dest_file = os.path.join(backup_path, name)
                if log_callback:
                    log_callback(f"Fazendo backup Apollo: {name} -> backup/")
                shutil.copy2(full_path, dest_file)
                copied_count += 1
        
        if log_callback:
            log_callback(f"Backup do Apollo concluído. {copied_count} arquivos (EXE/DLL) copiados para {backup_path}")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Erro durante backup do Apollo (EXE/DLL): {str(e)}")
        return False

def execute_script_as_admin(script_path, log_callback=None, parameters=""):
    """
    Runs the selected script elevated as Administrator and blocks/waits for completion.
    On Linux, simulates this by waiting and logging.
    """
    if log_callback:
        log_callback(f"Preparando para executar script: {script_path} {parameters}".strip())
        
    if platform.system() != "Windows":
        if log_callback:
            log_callback("[Linux SIMULADO] Solicitando permissão de Administrador (sudo/runas)...")
            log_callback(f"[Linux SIMULADO] Executando: {script_path} {parameters}".strip())
        time.sleep(2)
        if log_callback:
            log_callback("[Linux SIMULADO] Execução simulada finalizada com sucesso.")
        return True
        
    if not os.path.exists(script_path):
        if log_callback:
            log_callback(f"Erro: Script não encontrado no caminho especificado: {script_path}")
        return False

    import ctypes

    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("fMask", ctypes.c_ulong),
            ("hwnd", ctypes.c_void_p),
            ("lpVerb", ctypes.c_wchar_p),
            ("lpFile", ctypes.c_wchar_p),
            ("lpParameters", ctypes.c_wchar_p),
            ("lpDirectory", ctypes.c_wchar_p),
            ("nShow", ctypes.c_int),
            ("hInstApp", ctypes.c_void_p),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", ctypes.c_wchar_p),
            ("hkeyClass", ctypes.c_void_p),
            ("dwHotKey", ctypes.c_ulong),
            ("hIconOrMonitor", ctypes.c_void_p),
            ("hProcess", ctypes.c_void_p)
        ]
    
    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    info = SHELLEXECUTEINFO()
    info.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.hwnd = None
    info.lpVerb = "runas"  # Prompts UAC elevation dialog
    info.lpFile = script_path
    info.lpParameters = parameters if parameters else None
    info.lpDirectory = os.path.dirname(script_path)
    info.nShow = 1  # SW_SHOWNORMAL
    
    if log_callback:
        log_callback("Aguardando confirmação do Controle de Conta de Usuário (UAC)...")
        
    try:
        success = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info))
        if not success:
            err = ctypes.GetLastError()
            if log_callback:
                log_callback(f"Execução negada ou erro no Windows UAC: Código {err}")
            return False
            
        hProcess = info.hProcess
        if hProcess:
            if log_callback:
                log_callback("Processo de Scripts do NBS iniciado. Aguardando finalização...")
            INFINITE = 0xFFFFFFFF
            ctypes.windll.kernel32.WaitForSingleObject(hProcess, INFINITE)
            ctypes.windll.kernel32.CloseHandle(hProcess)
            if log_callback:
                log_callback("Processo de atualização do banco finalizado.")
            return True
        else:
            if log_callback:
                log_callback("Processo iniciado (sem identificador de espera retornado).")
            return True
    except Exception as e:
        if log_callback:
            log_callback(f"Falha na execução do processo como administrador: {str(e)}")
        return False

def copy_dir_recursive(src, dst, log_callback=None):
    """
    Recursively copies a folder from src to dst.
    """
    if not os.path.exists(src):
        return
        
    os.makedirs(dst, exist_ok=True)
    
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        
        if os.path.isdir(src_item):
            copy_dir_recursive(src_item, dst_item, log_callback)
        else:
            try:
                # Copy file and metadata (permissions/times)
                shutil.copy2(src_item, dst_item)
                if log_callback:
                    log_callback(f"Copiado: {item}")
            except Exception as e:
                if os.path.exists(dst_item):
                    if log_callback:
                        log_callback(f"Arquivo {item} em uso ou bloqueado. Tentando renomear existente...")
                    try:
                        base, ext = os.path.splitext(item)
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
                        new_name = f"{base}_{timestamp}{ext}"
                        dst_item_renamed = os.path.join(dst, new_name)
                        os.rename(dst_item, dst_item_renamed)
                        if log_callback:
                            log_callback(f"Renomeado antigo {item} para {new_name}")
                        shutil.copy2(src_item, dst_item)
                        if log_callback:
                            log_callback(f"Copiado (após renomear): {item}")
                    except Exception as err:
                        if log_callback:
                            log_callback(f"Falha ao renomear/sobrescrever {item}: {str(err)}")
                        raise e
                else:
                    if log_callback:
                        log_callback(f"Erro ao copiar {item}: {str(e)}")
                    raise e

def distribute_to_destination(source_dir, dst_path, log_callback=None):
    r"""
    Copies files from source_dir to dst_path.
    If on Linux and path is UNC (\\IP\path), runs a simulated copy log instead.
    """
    if not os.path.exists(source_dir):
        if log_callback:
            log_callback(f"Diretório de origem não existe: {source_dir}")
        return False
        
    is_unc = dst_path.startswith("\\\\") or (dst_path.startswith("//") and not os.path.exists(dst_path))
    
    if platform.system() != "Windows" and is_unc:
        # Simulate copy on Linux for Windows UNC paths
        if log_callback:
            log_callback(f"[Linux SIMULADO] Conectando ao compartilhamento rede {dst_path}...")
        time.sleep(1)
        
        def simulate_dir(src, current_rel=""):
            for item in os.listdir(src):
                full_src = os.path.join(src, item)
                rel_path = os.path.join(current_rel, item) if current_rel else item
                if os.path.isdir(full_src):
                    simulate_dir(full_src, rel_path)
                else:
                    if log_callback:
                        log_callback(f"[Linux SIMULADO] Copiando para {dst_path}\\{rel_path.replace('/', '\\')}... Concluído")
        try:
            simulate_dir(source_dir)
            if log_callback:
                log_callback(f"[Linux SIMULADO] Distribuição concluída com sucesso para {dst_path}")
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"[Linux SIMULADO] Erro ao simular cópia: {str(e)}")
            return False
    else:
        # Real copy (for Windows or Linux local-paths)
        try:
            if log_callback:
                log_callback(f"Iniciando cópia para {dst_path}...")
            copy_dir_recursive(source_dir, dst_path, log_callback)
            if log_callback:
                log_callback(f"Distribuição concluída para {dst_path}")
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"Erro ao distribuir para {dst_path}: {str(e)}")
            return False

def compress_folder(folder_path, archive_type='zip', log_callback=None):
    """
    Compresses folder_path recursively using zipfile with ZIP_DEFLATED and level 9.
    Creates the archive in the parent directory of folder_path.
    Returns the absolute path of the created archive file, or None on failure.
    """
    import zipfile

    if not os.path.exists(folder_path):
        if log_callback:
            log_callback(f"Erro: Pasta a ser compactada não existe: {folder_path}")
        return None

    parent_dir = os.path.dirname(folder_path)
    folder_name = os.path.basename(folder_path)
    archive_path = os.path.join(parent_dir, f"{folder_name}.{archive_type}")

    try:
        if log_callback:
            log_callback(f"Iniciando compactação máxima (.zip) da pasta: {folder_name}...")

        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(folder_name, os.path.relpath(file_path, folder_path))
                    zipf.write(file_path, arcname)

        if log_callback:
            log_callback(f"Pasta compactada com sucesso: {os.path.basename(archive_path)}")
        return archive_path
    except Exception as e:
        if log_callback:
            log_callback(f"Erro durante a compactação: {str(e)}")
        if os.path.exists(archive_path):
            try:
                os.remove(archive_path)
            except Exception:
                pass
        return None

def calculate_local_md5(filepath):
    """Calcula o hash MD5 de um arquivo local para consistência."""
    if not os.path.exists(filepath):
        return None
    try:
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest().lower()
    except Exception:
        return None

def is_backup_up_to_date(nbs_path, backup_dir, compress_backup):
    """
    Checks if a backup already exists (folder or zip) and is up-to-date
    with the executable files inside nbs_path.
    """
    if not os.path.exists(nbs_path):
        return False

    try:
        # Get source executables and their sizes
        src_files = {}
        for name in os.listdir(nbs_path):
            full_path = os.path.join(nbs_path, name)
            if os.path.isfile(full_path) and name.lower().endswith(".exe"):
                src_files[name] = os.path.getsize(full_path)

        if not src_files:
            # Nothing to backup, so technically it is up-to-date
            return True

        if compress_backup:
            # We expect a zip file: parent_dir/backup.zip
            parent_dir = os.path.dirname(backup_dir)
            zip_path = os.path.join(parent_dir, "backup.zip")
            if not os.path.exists(zip_path):
                return False

            import zipfile
            # Inspect ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zip_infos = {os.path.basename(info.filename): info.file_size for info in zipf.infolist() if not info.is_dir()}
                
                # Check if all source files are present in zip with the same size
                for name, size in src_files.items():
                    if name not in zip_infos or zip_infos[name] != size:
                        return False
            return True
        else:
            # We expect a directory: backup_dir/
            if not os.path.exists(backup_dir):
                return False

            for name, size in src_files.items():
                dest_file = os.path.join(backup_dir, name)
                if not os.path.exists(dest_file) or os.path.getsize(dest_file) != size:
                    return False
            return True

    except Exception:
        return False


def download_http_file(url, local_filepath, progress_callback=None, check_pause_cancel=None):
    """
    Downloads a file from url to local_filepath via HTTP using urllib.request.
    Supports pause/cancel validation and progress reporting via callbacks.
    """
    import urllib.request
    import ssl

    try:
        # Create request with a User-Agent to avoid HTTP 403 Forbidden issues
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        if check_pause_cancel:
            check_pause_cancel()

        # Try to download using standard SSL verification first.
        # If it fails with SSL verification errors, fallback to unverified context.
        try:
            response = urllib.request.urlopen(req, timeout=15)
        except Exception as ssl_err:
            ssl_err_str = str(ssl_err).lower()
            if "certificate_verify_failed" in ssl_err_str or "certificate verify failed" in ssl_err_str:
                context = ssl._create_unverified_context()
                response = urllib.request.urlopen(req, timeout=15, context=context)
            else:
                raise ssl_err

        with response:
            total_size = int(response.info().get("Content-Length", 0))
            
            # Ensure output folder exists
            os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
            
            downloaded = 0
            chunk_size = 65536  # 64 KB
            
            with open(local_filepath, "wb") as f:
                while True:
                    if check_pause_cancel:
                        check_pause_cancel()
                        
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                        
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        return True
    except Exception as e:
        # Clean up partial file on failure if it exists
        if os.path.exists(local_filepath):
            try:
                os.remove(local_filepath)
            except Exception:
                pass
        raise e


