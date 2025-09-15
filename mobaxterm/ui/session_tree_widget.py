from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QAction, 
                             QInputDialog, QMessageBox, QLineEdit, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QKeyEvent, QDrag, QBrush

class SessionTreeWidget(QTreeWidget):
    context_menu_requested = pyqtSignal(str, object)
    session_double_clicked = pyqtSignal(object)
    rename_requested = pyqtSignal(str, object)
    session_moved = pyqtSignal(int, str)  # Новый сигнал: session_index, target_folder
    
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
        
        # Включаем поддержку drag & drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Установка фокуса для обработки клавиш
        self.setFocusPolicy(Qt.StrongFocus)
    
    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика по элементу"""
        if item.data(0, Qt.UserRole) == "session":
            self.session_double_clicked.emit(item)
    
    def mousePressEvent(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши для перетаскивания"""
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        item = self.itemAt(self.drag_start_position)
        if not item:
            return
            
        item_type = item.data(0, Qt.UserRole)
        if item_type not in ["session", "folder"]:
            return
            
        # Создаем drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        
        if item_type == "session":
            session_index = item.data(0, Qt.UserRole + 1)
            mime_data.setText(f"session:{session_index}")
        else:  # folder
            folder_name = item.data(0, Qt.UserRole + 1)
            mime_data.setText(f"folder:{folder_name}")
            
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)
    
    def dragEnterEvent(self, event):
        """Разрешаем drag enter"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """Обработка движения при перетаскивании"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Обработка drop"""
        if not event.mimeData().hasText():
            return
            
        mime_data = event.mimeData().text()
        target_item = self.itemAt(event.pos())
        
        # Определяем тип перетаскиваемого элемента
        if mime_data.startswith("session:"):
            session_index = int(mime_data.split(":")[1])
            self.handle_session_drop(session_index, target_item, event.pos())
        elif mime_data.startswith("folder:"):
            folder_name = mime_data.split(":")[1]
            self.handle_folder_drop(folder_name, target_item, event.pos())
            
        event.acceptProposedAction()
    
    def handle_session_drop(self, session_index, target_item, drop_position):
        """Обработка drop сессии"""
        if not target_item:
            # Бросили на пустое место - удаляем из папки
            self.session_moved.emit(session_index, None)
            return
            
        target_type = target_item.data(0, Qt.UserRole)
        
        if target_type == "folder":
            # Бросили на папку - перемещаем в эту папку
            folder_name = target_item.data(0, Qt.UserRole + 1)
            self.session_moved.emit(session_index, folder_name)
        elif target_type == "session":
            # Бросили на другую сессию - определяем куда именно
            parent = target_item.parent()
            if parent and parent.data(0, Qt.UserRole) == "folder":
                # Бросили на сессию внутри папки - перемещаем в эту папку
                folder_name = parent.data(0, Qt.UserRole + 1)
                self.session_moved.emit(session_index, folder_name)
            else:
                # Бросили на сессию без папки - удаляем из папки
                self.session_moved.emit(session_index, None)
    
    def handle_folder_drop(self, folder_name, target_item, drop_position):
        """Обработка drop папки"""
        # Для простоты не будем поддерживать перетаскивание папок друг на друга
        # Можно добавить эту функциональность позже если нужно
        pass
    
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
    # В session_tree_widget.py добавьте методы:

    def startDrag(self, supportedActions):
        """Начало перетаскивания с визуальными эффектами"""
        item = self.currentItem()
        if item:
            item.setBackground(0, QColor("#fff3cd"))  # Подсветка перетаскиваемого элемента
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        """Обработка drop с восстановлением внешнего вида"""
        super().dropEvent(event)
        # Восстанавливаем нормальный вид всех элементов
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setBackground(0, QBrush())
            self.restore_item_appearance(item)
        
    def restore_item_appearance(self, item):
        """Рекурсивное восстановление внешнего вида элементов"""
        if not item:
            return
        item.setBackground(0, QBrush())
        for i in range(item.childCount()):
            self.restore_item_appearance(item.child(i))