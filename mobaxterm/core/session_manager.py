from typing import List, Optional
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
import json
import os
from mobaxterm.models.session import Session

class SessionManager:
    def __init__(self, config_file: str = "sessions.json"):
        self.sessions: List[Session] = []
        self.config_file = config_file
        self.load_sessions()
    
    def add_session(self, session: Session) -> None:
        self.sessions.append(session)
        self.save_sessions()
        return len(self.sessions) - 1
    
    def update_session(self, index: int, session: Session) -> bool:
        if 0 <= index < len(self.sessions):
            self.sessions[index] = session
            self.save_sessions()
            return True
        return False
    
    def delete_session(self, index: int) -> bool:
        if 0 <= index < len(self.sessions):
            self.sessions.pop(index)
            self.save_sessions()
            return True
        return False
    
    def get_session(self, index: int) -> Optional[Session]:
        if 0 <= index < len(self.sessions):
            return self.sessions[index]
        return None
    
    def get_all_sessions(self) -> List[Session]:
        return self.sessions.copy()
    
    def clear_sessions(self) -> None:
        self.sessions.clear()
        self.save_sessions()
    
    def save_sessions(self) -> None:
        try:
            data = [session.to_dict() for session in self.sessions]
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def load_sessions(self) -> None:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = [Session.from_dict(session_data) for session_data in data]
        except Exception as e:
            print(f"Error loading sessions: {e}")
    
    def update_session_list_widget(self, list_widget: QListWidget) -> None:
        list_widget.clear()
        for i, session in enumerate(self.sessions):
            item = QListWidgetItem(session.host)  # Только хост
            item.setData(Qt.UserRole, i)
            list_widget.addItem(item)
    
    def confirm_delete_session(self, parent, session_name: str) -> bool:
        reply = QMessageBox.question(
            parent, 
            "Confirm Delete", 
            f"Are you sure you want to delete session:\n{session_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

# Добавьте в класс SessionManager метод для подтверждения удаления:
def confirm_delete_session(self, parent, session_name: str) -> bool:
    reply = QMessageBox.question(
        parent, 
        "Confirm Delete", 
        f"Are you sure you want to delete session:\n{session_name}?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    return reply == QMessageBox.Yes