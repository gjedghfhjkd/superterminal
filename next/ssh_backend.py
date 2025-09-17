import paramiko
import logging
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

class SSHBackend(QObject):
    output = pyqtSignal(str)
    status = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        try:
            logging.getLogger('paramiko').setLevel(logging.WARNING)
        except Exception:
            pass
        self.client = None
        self.chan = None
        self._run = False

    def connect(self, host, port, username, password=None, auth_method='password', key_filename=None, passphrase=None):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kw = dict(hostname=host, port=port, username=username, timeout=10)
            if auth_method == 'key':
                kw.update(dict(key_filename=key_filename, passphrase=passphrase, allow_agent=True, look_for_keys=True))
            else:
                kw.update(dict(password=password, allow_agent=False, look_for_keys=False))
            self.client.connect(**kw)
            self.chan = self.client.invoke_shell(term='xterm-256color', width=160, height=40)
            self.chan.settimeout(0.0)
            self._run = True
            t = threading.Thread(target=self._reader, daemon=True)
            t.start()
            self.status.emit(True, f'Connected to {host}:{port}')
        except Exception as e:
            self.status.emit(False, f'SSH error: {e}')

    def _reader(self):
        while self._run:
            try:
                if self.chan and self.chan.recv_ready():
                    data = self.chan.recv(32768)
                    try:
                        s = data.decode('utf-8')
                    except Exception:
                        s = data.decode('utf-8', errors='ignore')
                    if s:
                        self.output.emit(s)
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    def send(self, data: str):
        try:
            if self.chan:
                self.chan.send(data)
        except Exception:
            pass

    def resize(self, cols: int, rows: int):
        try:
            if self.chan:
                self.chan.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def close(self):
        self._run = False
        try:
            if self.chan: self.chan.close()
        except Exception: pass
        try:
            if self.client: self.client.close()
        except Exception: pass
        self.status.emit(False, 'Disconnected')

