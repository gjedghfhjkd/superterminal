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

            norm = self.sftp.normalize(candidate)
            # Test access by listing
            _ = self.sftp.listdir(norm)
            self.current_path = norm
            self.list_dir(norm)
        except Exception as e:
            self.connection_status.emit(True, f"⚠️ Cannot change directory: {str(e)}")

    def up_dir(self):
        if not self.current_path:
            return
        parent = os.path.dirname(self.current_path.rstrip('/')) or '/'
        self.change_dir(parent)

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

