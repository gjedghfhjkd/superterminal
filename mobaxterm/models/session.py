from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

@dataclass
class Session:
    type: str  # 'SSH' or 'SFTP'
    host: str
    port: int
    username: Optional[str] = None
    terminal_settings: bool = False
    network_settings: bool = False
    bookmark_settings: bool = False
    folder: Optional[str] = None
    
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
            terminal_settings=data.get('terminal_settings', False),
            network_settings=data.get('network_settings', False),
            bookmark_settings=data.get('bookmark_settings', False),
            folder=data.get('folder')
        )