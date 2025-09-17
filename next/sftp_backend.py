import paramiko
from PyQt5.QtCore import QObject, pyqtSignal

class SFTPBackend(QObject):
    status = pyqtSignal(bool, str)
    listing = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        self.client = None
        self.sftp = None

    def connect(self, host, port, username, password=None, auth_method='password', key_filename=None, passphrase=None):
        try:
            self.client = paramiko.Transport((host, port))
            if auth_method == 'key':
                pkey = None
                if key_filename:
                    try:
                        pkey = paramiko.RSAKey.from_private_key_file(key_filename, password=passphrase)
                    except Exception:
                        pkey = None
                self.client.connect(username=username, pkey=pkey)
            else:
                self.client.connect(username=username, password=password)
            self.sftp = paramiko.SFTPClient.from_transport(self.client)
            self.status.emit(True, 'SFTP connected')
        except Exception as e:
            self.status.emit(False, f'SFTP error: {e}')

    def listdir(self, path: str):
        try:
            entries = []
            for a in self.sftp.listdir_attr(path):
                entries.append(dict(filename=a.filename, st_mode=a.st_mode, st_size=a.st_size))
            self.listing.emit(path, entries)
        except Exception as e:
            self.status.emit(False, f'SFTP list error: {e}')

    def close(self):
        try:
            if self.sftp: self.sftp.close()
        except Exception: pass
        try:
            if self.client: self.client.close()
        except Exception: pass
        self.status.emit(False, 'SFTP disconnected')

