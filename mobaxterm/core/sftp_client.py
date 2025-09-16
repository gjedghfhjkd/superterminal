import paramiko
from PyQt5.QtCore import QObject, pyqtSignal
import os
import stat
import time


class SFTPClient(QObject):
    connection_status = pyqtSignal(bool, str)
    remote_listing = pyqtSignal(str, list)  # path, entries: [{name, is_dir, size, mtime, mode}]

    def __init__(self):
        super().__init__()
        self.client = None
        self.sftp = None
        self.is_connected = False
        self.current_path = None

    def connect(self, host, port=22, username=None, password=None, auth_method='password', key_filename=None, passphrase=None, allow_agent=True, look_for_keys=True):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': 10,
            }

            if auth_method == 'key':
                connect_kwargs['key_filename'] = key_filename
                connect_kwargs['passphrase'] = passphrase
                connect_kwargs['allow_agent'] = True if allow_agent is None else allow_agent
                connect_kwargs['look_for_keys'] = True if look_for_keys is None else look_for_keys
            else:
                connect_kwargs['password'] = password
                connect_kwargs['allow_agent'] = False
                connect_kwargs['look_for_keys'] = False

            self.client.connect(**connect_kwargs)
            self.sftp = self.client.open_sftp()
            # Determine initial directory
            try:
                self.current_path = self.sftp.normalize('.')
            except Exception:
                try:
                    self.current_path = self.sftp.getcwd() or '/'
                except Exception:
                    self.current_path = '/'

            self.is_connected = True
            self.connection_status.emit(True, f"✅ SFTP connected to {host}:{port}")
            # Emit first listing
            self.list_dir(self.current_path)
        except paramiko.AuthenticationException:
            self.connection_status.emit(False, "❌ Authentication failed. Please check credentials.")
        except paramiko.SSHException as e:
            self.connection_status.emit(False, f"❌ SSH error: {str(e)}")
        except Exception as e:
            self.connection_status.emit(False, f"❌ SFTP connection error: {str(e)}")

    def _format_entry(self, attr):
        is_dir = stat.S_ISDIR(attr.st_mode)
        return {
            'name': getattr(attr, 'filename', ''),
            'is_dir': is_dir,
            'size': getattr(attr, 'st_size', 0),
            'mtime': getattr(attr, 'st_mtime', 0),
            'mode': getattr(attr, 'st_mode', 0),
        }

    def list_dir(self, path=None):
        if not self.is_connected or self.sftp is None:
            return
        target = path or self.current_path or '/'
        try:
            attrs = self.sftp.listdir_attr(target)
            entries = [self._format_entry(a) for a in attrs]
            # Sort: dirs first, then files; both alphabetically
            entries.sort(key=lambda e: (0 if e['is_dir'] else 1, e['name'].lower()))
            self.remote_listing.emit(target, entries)
        except Exception as e:
            self.connection_status.emit(True, f"⚠️ Failed to list '{target}': {str(e)}")

    def change_dir(self, new_path: str):
        if not self.is_connected or self.sftp is None:
            return
        try:
            # Normalize to absolute path
            if not new_path:
                new_path = self.current_path or '/'
            if not new_path.startswith('/'):
                base = self.current_path or '/'
                candidate = os.path.normpath(os.path.join(base, new_path))
            else:
                candidate = os.path.normpath(new_path)

            # Some SFTP servers don't support normalize for relative, build absolute
            try:
                norm = self.sftp.normalize(candidate)
            except Exception:
                norm = candidate
            # Ensure it's a directory
            try:
                st = self.sftp.stat(norm)
                if not stat.S_ISDIR(getattr(st, 'st_mode', 0)):
                    # If it's a file, use its directory
                    norm = os.path.dirname(norm) or '/'
            except Exception:
                # Fallback: try listdir to confirm
                try:
                    _ = self.sftp.listdir(norm)
                except Exception as e:
                    self.connection_status.emit(True, f"⚠️ Cannot change directory: {str(e)}")
                    return
            self.current_path = norm
            self.list_dir(norm)
        except Exception as e:
            self.connection_status.emit(True, f"⚠️ Cannot change directory: {str(e)}")

    def up_dir(self):
        if not self.current_path:
            return
        parent = os.path.dirname(self.current_path.rstrip('/')) or '/'
        self.change_dir(parent)

    # ===== Transfers =====
    def upload_files(self, local_paths, remote_dir):
        if not self.is_connected or self.sftp is None:
            return
        try:
            remote_dir = self.sftp.normalize(remote_dir or self.current_path or '/')
        except Exception:
            remote_dir = self.current_path or '/'
        uploaded = 0
        failed = 0
        for lp in local_paths or []:
            try:
                if os.path.isdir(lp):
                    self._upload_dir_recursive(lp, os.path.join(remote_dir, os.path.basename(lp)))
                else:
                    target = os.path.join(remote_dir, os.path.basename(lp)).replace('\\', '/')
                    self._ensure_remote_dir(remote_dir)
                    self.sftp.put(lp, target)
                uploaded += 1
            except Exception as e:
                failed += 1
                self.connection_status.emit(True, f"⚠️ Upload failed for {os.path.basename(lp)}: {str(e)}")
        # Refresh listing
        self.list_dir(remote_dir)
        if failed == 0:
            self.connection_status.emit(True, f"✅ Uploaded {uploaded} item(s) to {remote_dir}")
        else:
            self.connection_status.emit(True, f"⛔ Uploaded {uploaded}, failed {failed} to {remote_dir}")

    def _ensure_remote_dir(self, path):
        # Create remote directories recursively
        parts = []
        p = path
        while p not in ('', '/', None):
            parts.append(p)
            p = os.path.dirname(p.rstrip('/'))
        for dirp in reversed(parts):
            try:
                self.sftp.listdir(dirp)
            except Exception:
                try:
                    self.sftp.mkdir(dirp)
                except Exception:
                    pass

    def _upload_dir_recursive(self, local_dir, remote_dir):
        self._ensure_remote_dir(remote_dir)
        for root, dirs, files in os.walk(local_dir):
            rel = os.path.relpath(root, local_dir)
            target_root = remote_dir if rel == '.' else os.path.join(remote_dir, rel).replace('\\', '/')
            self._ensure_remote_dir(target_root)
            for d in dirs:
                self._ensure_remote_dir(os.path.join(target_root, d).replace('\\', '/'))
            for f in files:
                lp = os.path.join(root, f)
                rp = os.path.join(target_root, f).replace('\\', '/')
                self.sftp.put(lp, rp)

    def download_files(self, remote_paths, local_dir):
        if not self.is_connected or self.sftp is None:
            return
        try:
            if not os.path.isdir(local_dir):
                os.makedirs(local_dir, exist_ok=True)
        except Exception:
            pass
        downloaded = 0
        failed = 0
        for rp in remote_paths or []:
            try:
                # Determine if remote is dir
                try:
                    st = self.sftp.stat(rp)
                    is_dir = stat.S_ISDIR(getattr(st, 'st_mode', 0))
                except IOError:
                    is_dir = False
                if is_dir:
                    self._download_dir_recursive(rp, os.path.join(local_dir, os.path.basename(rp)))
                else:
                    lp = os.path.join(local_dir, os.path.basename(rp))
                    self.sftp.get(rp, lp)
                downloaded += 1
            except Exception as e:
                failed += 1
                self.connection_status.emit(True, f"⚠️ Download failed for {os.path.basename(rp)}: {str(e)}")
        # Refresh listing on current dir
        self.list_dir(self.current_path)
        if failed == 0:
            self.connection_status.emit(True, f"✅ Downloaded {downloaded} item(s) to {local_dir}")
        else:
            self.connection_status.emit(True, f"⛔ Downloaded {downloaded}, failed {failed} to {local_dir}")

    def _download_dir_recursive(self, remote_dir, local_dir):
        try:
            os.makedirs(local_dir, exist_ok=True)
        except Exception:
            pass
        for entry in self.sftp.listdir_attr(remote_dir):
            name = getattr(entry, 'filename', '')
            rp = remote_dir.rstrip('/') + '/' + name
            lp = os.path.join(local_dir, name)
            if stat.S_ISDIR(entry.st_mode):
                self._download_dir_recursive(rp, lp)
            else:
                self.sftp.get(rp, lp)

    def disconnect(self):
        try:
            if self.sftp:
                self.sftp.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.is_connected = False
        self.connection_status.emit(False, "SFTP disconnected")

