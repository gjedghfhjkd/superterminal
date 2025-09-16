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
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(0.1)
            
            # Start reading thread
            self.read_thread = threading.Thread(target=self.read_output)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            self.connection_status.emit(True, f"✅ Connected to {host}:{port}")
            self.output_received.emit(f"Welcome to {host}\n")
            
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
        buffer = ""
        while self.is_connected:
            try:
                if self.shell and self.shell.recv_ready():
                    data = self.shell.recv(1024).decode('utf-8', errors='ignore')
                    if data:
                        buffer += data
                        if '\n' in buffer or '\r' in buffer:
                            lines = buffer.splitlines(True)
                            for line in lines[:-1]:
                                self.output_received.emit(line.strip())
                            buffer = lines[-1] if lines else ""
                    else:
                        time.sleep(0.1)
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
    
    def send_command(self, command):
        if self.is_connected and self.shell:
            try:
                self.shell.send(command + '\n')
            except Exception as e:
                self.output_received.emit(f"Error sending command: {str(e)}")
    
    def disconnect(self):
        self.is_connected = False
        if self.client:
            self.client.close()
        self.connection_status.emit(False, "Disconnected")