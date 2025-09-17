import paramiko
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

class SSH2(QObject):
    output_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self._client = None
        self._chan = None
        self._running = False
        self._reader = None

    def connect(self, host, port=22, username=None, password=None, auth_method='password', key_filename=None, passphrase=None, allow_agent=True, look_for_keys=False):
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs = dict(hostname=host, port=port, username=username, timeout=10)
            if auth_method == 'key':
                kwargs.update(dict(key_filename=key_filename, passphrase=passphrase, allow_agent=True if allow_agent is None else allow_agent, look_for_keys=True if look_for_keys is None else look_for_keys))
            else:
                kwargs.update(dict(password=password, allow_agent=False, look_for_keys=False))
            self._client.connect(**kwargs)
            # open PTY shell
            self._chan = self._client.invoke_shell(term='xterm-256color', width=160, height=40)
            self._chan.settimeout(0.0)
            self._running = True
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()
            self.connection_status.emit(True, f"✅ Connected to {host}:{port}")
        except Exception as e:
            self.connection_status.emit(False, f"❌ SSH2 connect error: {e}")

    def _read_loop(self):
        while self._running:
            try:
                if self._chan and self._chan.recv_ready():
                    data = self._chan.recv(32768)
                    try:
                        s = data.decode('utf-8')
                    except Exception:
                        s = data.decode('utf-8', errors='ignore')
                    if s:
                        self.output_received.emit(s)
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    def send(self, data: str):
        try:
            if self._chan and data is not None:
                self._chan.send(data)
        except Exception:
            pass

    def resize_pty(self, cols: int, rows: int):
        try:
            if self._chan:
                self._chan.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def disconnect(self):
        self._running = False
        try:
            if self._chan:
                self._chan.close()
        except Exception:
            pass
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
        self.connection_status.emit(False, "Disconnected")

