from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

@dataclass
class Session:
    type: str  # 'SSH' or 'SFTP'
    host: str
    port: int
    username: Optional[str] = None
    auth_method: str = "password"  # 'password' | 'key'
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    terminal_settings: bool = False
    network_settings: bool = False
    folder: Optional[str] = None 
    bookmark_settings: bool = False
    folder: Optional[str] = None
    def __post_init__(self):
        if self.folder and self.folder.startswith('/'):
            self.folder = self.folder[1:]
    def display_name(self) -> str:
        if self.type == 'SSH':
            username_part = f"({self.username})" if self.username else ""
            return f"SSH - {self.host}:{self.port} {username_part}".strip()
        else:
            return f"SFTP - {self.host}:{self.port} ({self.username})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'username': self.username,

            'auth_method': self.auth_method,
            'private_key_path': self.private_key_path,
            'private_key_passphrase': self.private_key_passphrase,
            'terminal_settings': self.terminal_settings,
            'network_settings': self.network_settings,
            'bookmark_settings': self.bookmark_settings,
            'folder': self.folder
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        return cls(
            type=data['type'],
            host=data['host'],
            port=data['port'],
            username=data['username'],
            auth_method=data.get('auth_method', 'password'),
            private_key_path=data.get('private_key_path'),
            private_key_passphrase=data.get('private_key_passphrase'),
            terminal_settings=data.get('terminal_settings', False),
            network_settings=data.get('network_settings', False),
            bookmark_settings=data.get('bookmark_settings', False),
            folder=data.get('folder')
        )