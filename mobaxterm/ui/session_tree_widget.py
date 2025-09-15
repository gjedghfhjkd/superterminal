from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QAction, 
                             QInputDialog, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent

class SessionTreeWidget(QTreeWidget):
    context_menu_requested = pyqtSignal(str, object)
    session_double_clicked = pyqtSignal(object)
    rename_requested = pyqtSignal(str, object)
    
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
        self.itemDoubleClicked.connect(self.on_item_double_clicked)  # Теперь метод существует
        
        # Установка фокуса для обработки клавиш
        self.setFocusPolicy(Qt.StrongFocus)
    
    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика по элементу"""
        if item.data(0, Qt.UserRole) == "session":
            self.session_double_clicked.emit(item)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатий клавиш"""
        # Обработка клавиши F2 - переименование
        if event.key() == Qt.Key_F2:
            item = self.currentItem()
            if item:
                item_type = item.data(0, Qt.UserRole)
                if item_type in ["folder", "session"]:
                    self.rename_requested.emit(item_type, item)
            event.accept()
            return
            
        # Обработка клавиши Delete - удаление
        elif event.key() == Qt.Key_Delete:
            item = self.currentItem()
            if item:
                item_type = item.data(0, Qt.UserRole)
                if item_type == "folder":
                    self.context_menu_requested.emit("delete_folder", item)
                elif item_type == "session":
                    self.context_menu_requested.emit("delete_session", item)
            event.accept()
            return
            
        super().keyPressEvent(event)
    
    def on_context_menu(self, position):
        """Обработка контекстного меню"""
        item = self.itemAt(position)
        menu = QMenu(self)
        
        if item:
            item_type = item.data(0, Qt.UserRole)
            if item_type == "folder":
                # Добавляем действие для переключения папки
                toggle_action = QAction("🔽 Expand/Collapse", self)
                add_session_action = QAction("➕ Add Session", self)
                rename_action = QAction("✏️ Rename Folder", self)
                delete_folder_action = QAction("🗑️ Delete Folder", self)
                
                menu.addAction(toggle_action)
                menu.addSeparator()
                menu.addAction(add_session_action)
                menu.addAction(rename_action)
                menu.addAction(delete_folder_action)
                
                action = menu.exec_(self.mapToGlobal(position))
                
                if action == toggle_action:
                    item.setExpanded(not item.isExpanded())
                elif action == add_session_action:
                    self.context_menu_requested.emit("add_session_to_folder", item)
                elif action == rename_action:
                    self.rename_requested.emit("folder", item)
                elif action == delete_folder_action:
                    self.context_menu_requested.emit("delete_folder", item)
            else:
                # Контекстное меню для сессии
                edit_action = QAction("✏️ Edit Session", self)
                rename_action = QAction("📝 Rename Session", self)
                move_action = QAction("➡️ Move to Folder", self)
                delete_action = QAction("🗑️ Delete Session", self)
                
                menu.addAction(edit_action)
                menu.addAction(rename_action)
                menu.addAction(move_action)
                menu.addAction(delete_action)
                
                action = menu.exec_(self.mapToGlobal(position))
                
                if action == edit_action:
                    self.context_menu_requested.emit("edit_session", item)
                elif action == rename_action:
                    self.rename_requested.emit("session", item)
                elif action == move_action:
                    self.context_menu_requested.emit("move_session", item)
                elif action == delete_action:
                    self.context_menu_requested.emit("delete_session", item)
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