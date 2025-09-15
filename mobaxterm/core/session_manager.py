from typing import List, Optional, Dict, Any
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
import json
import os
from ..models.session import Session

class SessionManager:
    def __init__(self, config_file: str = "sessions.json"):
        self.sessions: List[Session] = []
        self.folders: Dict[str, List[int]] = {}  # folder_name -> list of session indices
        self.config_file = config_file
        self.load_sessions()
    
    def add_session(self, session: Session, folder: str = None) -> int:
        session_index = len(self.sessions)
        self.sessions.append(session)
        
        if folder:
            if folder not in self.folders:
                self.folders[folder] = []
            self.folders[folder].append(session_index)
        
        self.save_sessions()
        return session_index
    
    def update_session(self, index: int, session: Session) -> bool:
        if 0 <= index < len(self.sessions):
            self.sessions[index] = session
            self.save_sessions()
            return True
        return False
    
    def delete_session(self, index: int) -> bool:
        if 0 <= index < len(self.sessions):
            self.sessions.pop(index)
            
            # Remove from all folders
            for folder_sessions in self.folders.values():
                if index in folder_sessions:
                    folder_sessions.remove(index)
            
            # Update indices in folders (decrement indices greater than deleted index)
            for folder_name in self.folders:
                self.folders[folder_name] = [
                    i if i < index else i - 1 
                    for i in self.folders[folder_name] 
                    if i != index
                ]
            
            self.save_sessions()
            return True
        return False
    
    def add_folder(self, folder_name: str) -> bool:
        if folder_name and folder_name not in self.folders:
            self.folders[folder_name] = []
            self.save_sessions()
            return True
        return False
    
    def delete_folder(self, folder_name: str) -> bool:
        if folder_name in self.folders:
            del self.folders[folder_name]
            self.save_sessions()
            return True
        return False
    
    def move_session_to_folder(self, session_index: int, folder_name: str) -> bool:
        # Remove from all folders first
        for folder_sessions in self.folders.values():
            if session_index in folder_sessions:
                folder_sessions.remove(session_index)
        
        # Add to new folder if specified
        if folder_name:
            if folder_name not in self.folders:
                self.folders[folder_name] = []
            self.folders[folder_name].append(session_index)
        
        self.save_sessions()
        return True
    
    def get_session(self, index: int) -> Optional[Session]:
        if 0 <= index < len(self.sessions):
            return self.sessions[index]
        return None
    
    def get_all_sessions(self) -> List[Session]:
        return self.sessions.copy()
    
    def get_sessions_in_folder(self, folder_name: str) -> List[Session]:
        if folder_name in self.folders:
            return [self.sessions[i] for i in self.folders[folder_name]]
        return []
    
    def get_all_folders(self) -> List[str]:
        return list(self.folders.keys())
    
    def clear_sessions(self) -> None:
        self.sessions.clear()
        self.folders.clear()
        self.save_sessions()
    
    def save_sessions(self) -> None:
        try:
            data = {
                'sessions': [session.to_dict() for session in self.sessions],
                'folders': self.folders,
                'version': 2  # Добавляем версию для совместимости
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def load_sessions(self) -> None:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                    # Проверяем формат файла
                    if isinstance(data, list):
                        # Старый формат (только список сессий)
                        self.sessions = [Session.from_dict(session_data) for session_data in data]
                        self.folders = {}
                        print("Converted old format to new format")
                        self.save_sessions()  # Сохраняем в новом формате
                    elif isinstance(data, dict):
                        # Новый формат
                        self.sessions = [Session.from_dict(session_data) for session_data in data.get('sessions', [])]
                        self.folders = data.get('folders', {})
        except Exception as e:
            print(f"Error loading sessions: {e}")
            # Если файл поврежден, создаем заново
            self.sessions = []
            self.folders = {}
    
    def update_session_list_widget(self, list_widget: QListWidget) -> None:
        list_widget.clear()
        for i, session in enumerate(self.sessions):
            item = QListWidgetItem(session.host)
            item.setData(Qt.UserRole, i)
            list_widget.addItem(item)
    def rename_folder(self, old_name, new_name):
        """Переименовать папку"""
        if old_name not in self.folders:
            return False
            
        if new_name in self.folders:
            # Папка с таким именем уже существует
            return False
            
        # Переименовываем папку
        self.folders[new_name] = self.folders.pop(old_name)
        
        # Обновляем ссылки на папку в сессиях
        for session in self.sessions:
            if session.folder == old_name:
                session.folder = new_name
        
        self.save_sessions()
        return True
    def confirm_delete_session(self, parent, session_name: str) -> bool:
        reply = QMessageBox.question(
            parent, 
            "Confirm Delete", 
            f"Are you sure you want to delete session:\n{session_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def delete_folder(self, folder_name: str) -> bool:
        if folder_name in self.folders:
            # Получаем индексы сессий в этой папке
            session_indices_to_delete = self.folders[folder_name].copy()
            
            # Сортируем в обратном порядке для правильного удаления
            session_indices_to_delete.sort(reverse=True)
            
            # Удаляем сессии
            for index in session_indices_to_delete:
                if 0 <= index < len(self.sessions):
                    self.sessions.pop(index)
            
            # Удаляем саму папку
            del self.folders[folder_name]
            
            # Обновляем индексы во всех оставшихся папках
            for other_folder_name, indices in self.folders.items():
                updated_indices = []
                for old_index in indices:
                    new_index = old_index
                    # Уменьшаем индекс для каждого удаленного элемента, который был выше
                    for deleted_index in session_indices_to_delete:
                        if old_index > deleted_index:
                            new_index -= 1
                    if new_index >= 0:
                        updated_indices.append(new_index)
                self.folders[other_folder_name] = updated_indices
            
            self.save_sessions()
            return True
        return False