import paramiko
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

class SSHClient(QObject):
    output_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.shell = None
        self.is_connected = False
        self.read_thread = None
        
    def connect(self, host, port=22, username=None, password=None, auth_method='password', key_filename=None, passphrase=None, allow_agent=True, look_for_keys=False):
        try:
            self.output_received.emit("🔗 Connecting to server...")
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try to connect with timeout
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': 10,
            }

            if auth_method == 'key':
                # Use provided private key file or fall back to agent/default keys
                connect_kwargs['key_filename'] = key_filename
                connect_kwargs['passphrase'] = passphrase
                connect_kwargs['allow_agent'] = True if allow_agent is None else allow_agent
                connect_kwargs['look_for_keys'] = True if look_for_keys is None else look_for_keys
                # Do not pass password when using key auth
            else:
                connect_kwargs['password'] = password
                connect_kwargs['allow_agent'] = False
                connect_kwargs['look_for_keys'] = False

            self.client.connect(**connect_kwargs)
            
            self.is_connected = True
            # Allocate interactive PTY shell with colors
            # Request a PTY with sane dimensions and xterm-256color
            self.shell = self.client.invoke_shell(term='xterm-256color', width=160, height=40)
            self.shell.settimeout(0.0)
            
            # Start reading thread
            self.read_thread = threading.Thread(target=self.read_output)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            self.connection_status.emit(True, f"✅ Connected to {host}:{port}")
            self.output_received.emit(f"Welcome to {host}\n")

            # Configure remote environment: prompt and terminal behavior
            self.configure_remote_environment()
            
        except paramiko.AuthenticationException:
            error_msg = "❌ Authentication failed. Please check credentials."
            self.connection_status.emit(False, error_msg)
            self.output_received.emit(error_msg)
            
        except paramiko.SSHException as e:
            error_msg = f"❌ SSH error: {str(e)}"
            self.connection_status.emit(False, error_msg)
            self.output_received.emit(error_msg)
            
        except Exception as e:
            error_msg = f"❌ Connection error: {str(e)}"
            self.connection_status.emit(False, error_msg)
            self.output_received.emit(error_msg)
    
    def read_output(self):
        while self.is_connected:
            try:
                if self.shell and self.shell.recv_ready():
                    data_bytes = self.shell.recv(32768)
                    if not data_bytes:
                        time.sleep(0.02)
                        continue
                    data = data_bytes.decode('utf-8', errors='ignore')
                    if data:
                        self.output_received.emit(data)
                else:
                    time.sleep(0.02)
            except Exception:
                time.sleep(0.1)
    
    def send_command(self, command):
        if self.is_connected and self.shell:
            try:
                self.shell.send(command + '\n')
            except Exception as e:
                self.output_received.emit(f"Error sending command: {str(e)}")

    def send_raw(self, data: str):
        if self.is_connected and self.shell and data is not None:
            try:
                self.shell.send(data)
            except Exception as e:
                self.output_received.emit(f"Error sending input: {str(e)}")

    def configure_remote_environment(self):
        """Set prompt to [user@host cwd]$ and enable sane terminal controls."""
        try:
            # Disable XON/XOFF so Ctrl+S/Ctrl+Q do not freeze terminal; set Ctrl-C/D
            self.shell.send("stty -ixon -ixoff intr ^C eof ^D 2>/dev/null\n")
            # Disable bracketed paste to avoid \x1b[?2004h noise
            # Use bash builtins when available; ignore errors on other shells
            self.shell.send("if [ -n \"$BASH_VERSION\" ]; then bind 'set enable-bracketed-paste off'; fi 2>/dev/null\n")
            # Set a simple, portable prompt. Works in bash/sh; \u,\h,\w are bash, but many servers use bash.
            # If not bash, this will be ignored harmlessly.
            self.shell.send("export PS1='[\\u@\\h \\w]\\$ '\n")
        except Exception:
            pass
    
    def disconnect(self):
        self.is_connected = False
        if self.client:
            self.client.close()
        self.connection_status.emit(False, "Disconnected")