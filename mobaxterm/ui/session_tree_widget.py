from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QAction, 
                             QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

class SessionTreeWidget(QTreeWidget):
    context_menu_requested = pyqtSignal(str, object)  # Изменяем порядок параметров
    session_double_clicked = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 6px;
                height: 30px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:hover {
                background-color: #f5f9ff;
                border: 1px solid #cce5ff;
            }
            QTreeWidget::item:selected:hover {
                background-color: #d1e7ff;
            }
        """)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def on_context_menu(self, position):
        item = self.itemAt(position)
        menu = QMenu(self)
        
        if item:
            item_type = item.data(0, Qt.UserRole)
            if item_type == "folder":
                # Контекстное меню для папки
                add_session_action = QAction("➕ Add Session", self)
                delete_folder_action = QAction("🗑️ Delete Folder", self)
                
                menu.addAction(add_session_action)
                menu.addAction(delete_folder_action)
                
                action = menu.exec_(self.mapToGlobal(position))
                
                if action == add_session_action:
                    self.context_menu_requested.emit("add_session_to_folder", item)
                elif action == delete_folder_action:
                    self.context_menu_requested.emit("delete_folder", item)
            else:
                # Контекстное меню для сессии
                edit_action = QAction("✏️ Edit Session", self)
                delete_action = QAction("🗑️ Delete Session", self)
                move_action = QAction("➡️ Move to Folder", self)
                
                menu.addAction(edit_action)
                menu.addAction(move_action)
                menu.addAction(delete_action)
                
                action = menu.exec_(self.mapToGlobal(position))
                
                if action == edit_action:
                    self.context_menu_requested.emit("edit_session", item)
                elif action == delete_action:
                    self.context_menu_requested.emit("delete_session", item)
                elif action == move_action:
                    self.context_menu_requested.emit("move_session", item)
        else:
            # Контекстное меню для пустой области
            add_folder_action = QAction("📁 Add Folder", self)
            add_session_action = QAction("➕ Add Session", self)
            
            menu.addAction(add_folder_action)
            menu.addAction(add_session_action)
            
            action = menu.exec_(self.mapToGlobal(position))
            
            if action == add_folder_action:
                self.context_menu_requested.emit("add_folder", None)
            elif action == add_session_action:
                self.context_menu_requested.emit("add_session", None)
    
    def on_item_double_clicked(self, item, column):
        if item.data(0, Qt.UserRole) == "session":
            self.session_double_clicked.emit(item)