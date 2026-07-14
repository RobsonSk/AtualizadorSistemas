import os
import re
from ftplib import FTP
import urllib.parse
from datetime import datetime

def parse_ftp_url(url_str):
    """
    Parses an FTP URL into (host, port, path).
    Supports formats like:
      - ftp://nbsi.com.br/sistemadelphi/modulos/oficiais
      - nbsi.com.br/sistemadelphi/modulos/oficiais
    """
    if not url_str.startswith("ftp://") and not url_str.startswith("ftps://"):
        url_str = "ftp://" + url_str
    parsed = urllib.parse.urlparse(url_str)
    host = parsed.hostname or ""
    port = parsed.port or 21
    path = parsed.path or "/"
    return host, port, path

class FTPClient:
    def __init__(self, host, port=21, user="anonymous", password=""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.ftp = None

    def connect(self):
        self.ftp = FTP()
        self.ftp.connect(self.host, self.port, timeout=15)
        self.ftp.login(self.user, self.password)
        # Enable UTF-8 encoding if supported by the server
        try:
            self.ftp.encoding = "utf-8"
        except Exception:
            pass

    def disconnect(self):
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                try:
                    self.ftp.close()
                except Exception:
                    pass
            self.ftp = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def list_subdirs(self, path):
        """
        Lists all subdirectories in the specified path.
        Uses MLSD first, then falls back to CWD testing.
        """
        if not self.ftp:
            return []
        
        subdirs = []
        try:
            # Try MLSD (Machine List Directory)
            for name, facts in self.ftp.mlsd(path):
                if name in (".", ".."):
                    continue
                if facts.get("type") == "dir":
                    subdirs.append(name)
            if subdirs:
                return sorted(subdirs)
        except Exception:
            pass
        
        # Fallback to CWD testing
        try:
            original_dir = self.ftp.pwd()
            self.ftp.cwd(path)
            items = self.ftp.nlst()
            for item in items:
                if item in (".", ".."):
                    continue
                try:
                    self.ftp.cwd(item)
                    subdirs.append(item)
                    self.ftp.cwd("..")
                except Exception:
                    pass
            self.ftp.cwd(original_dir)
        except Exception:
            pass
            
        return sorted(subdirs)

    def get_file_modification_time(self, filepath):
        """
        Gets the modification time of a file using MDTM command.
        Returns a datetime object or None if fails.
        """
        if not self.ftp:
            return None
        try:
            response = self.ftp.voidcmd(f"MDTM {filepath}")
            if response.startswith("213 "):
                time_str = response[4:].split(".")[0].strip()
                # Parse YYYYMMDDHHMMSS
                return datetime.strptime(time_str, "%Y%m%d%H%M%S")
        except Exception:
            pass
        return None

    def list_files_with_info(self, path):
        """
        Lists all files in a folder, returning a list of dicts:
        [{'name': str, 'modified': datetime, 'size': int}]
        """
        if not self.ftp:
            return []
        
        files = []
        
        # Try MLSD first
        try:
            for name, facts in self.ftp.mlsd(path):
                if name in (".", ".."):
                    continue
                if facts.get("type") == "file":
                    # Parse modification time
                    m_time = None
                    modify_fact = facts.get("modify")
                    if modify_fact:
                        try:
                            # MLSD returns YYYYMMDDHHMMSS or YYYYMMDDHHMMSS.xxx
                            time_str = modify_fact.split(".")[0]
                            m_time = datetime.strptime(time_str, "%Y%m%d%H%M%S")
                        except Exception:
                            pass
                    
                    if m_time is None:
                        m_time = self.get_file_modification_time(f"{path.rstrip('/')}/{name}")
                        
                    size = 0
                    try:
                        size = int(facts.get("size", 0))
                    except ValueError:
                        pass
                        
                    files.append({
                        "name": name,
                        "modified": m_time,
                        "size": size
                    })
            if files:
                return files
        except Exception:
            pass
            
        # Fallback to NLST + manual size/date fetch
        try:
            original_dir = self.ftp.pwd()
            self.ftp.cwd(path)
            items = self.ftp.nlst()
            for item in items:
                if item in (".", ".."):
                    continue
                # To check if it's a file, we check if we CAN'T cwd into it
                is_dir = False
                try:
                    self.ftp.cwd(item)
                    is_dir = True
                    self.ftp.cwd("..")
                except Exception:
                    pass
                
                if not is_dir:
                    full_remote_path = f"{path.rstrip('/')}/{item}"
                    m_time = self.get_file_modification_time(full_remote_path)
                    
                    size = 0
                    try:
                        size = self.ftp.size(item)
                    except Exception:
                        pass
                        
                    files.append({
                        "name": item,
                        "modified": m_time,
                        "size": size
                    })
            self.ftp.cwd(original_dir)
        except Exception:
            pass
            
        return files

    def download_file(self, remote_filepath, local_filepath, progress_callback=None, total_size=None):
        """
        Downloads a file and reports progress.
        """
        if not self.ftp:
            raise Exception("FTP client not connected.")
            
        if total_size is None:
            try:
                total_size = self.ftp.size(remote_filepath)
            except Exception:
                total_size = 0
                
        downloaded = 0
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
        
        with open(local_filepath, "wb") as f:
            def cb(block):
                nonlocal downloaded
                f.write(block)
                downloaded += len(block)
                if progress_callback:
                    progress_callback(downloaded, total_size)
                    
            self.ftp.retrbinary(f"RETR {remote_filepath}", cb)
        return True

    def get_file_md5(self, remote_filepath):
        """Tenta obter o MD5 de um arquivo remoto via comandos FTP MD5/XMD5."""
        if not self.ftp:
            return None
        for cmd in ["MD5", "XMD5"]:
            try:
                resp = self.ftp.sendcmd(f"{cmd} {remote_filepath}")
                if resp.startswith("25") or resp.startswith("200"):
                    parts = resp.split()
                    for part in parts:
                        part_clean = part.strip('"\'')
                        if len(part_clean) == 32 and all(c in "0123456789abcdefABCDEF" for c in part_clean):
                            return part_clean.lower()
            except Exception:
                pass
        return None
