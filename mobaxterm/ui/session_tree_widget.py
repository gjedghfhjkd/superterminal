from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QAction, 
                             QInputDialog, QMessageBox, QLineEdit, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt5.QtGui import QKeyEvent, QDrag

class SessionTreeWidget(QTreeWidget):
    context_menu_requested = pyqtSignal(str, object)
    session_double_clicked = pyqtSignal(object)
    rename_requested = pyqtSignal(str, object)
    session_moved = pyqtSignal(int, str, str)  # session_index, target_folder, current_folder
    folder_moved = pyqtSignal(str, object)  # folder_path, target_parent (str or None)
    
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
        # Автопрокрутка при DnD
        self.setAutoScroll(True)
        self.setAutoScrollMargin(24)
        self._drag_active = False
        self._last_drag_pos = None
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(50)
        self._auto_scroll_timer.timeout.connect(self._perform_auto_scroll)
        
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
            
        # Сохраняем информацию о текущей папке сессии
        current_folder = None
        if item_type == "session":
            parent = item.parent()
            if parent and parent.data(0, Qt.UserRole) == "folder":
                current_folder = parent.data(0, Qt.UserRole + 1)
        
        # Создаем drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        
        if item_type == "session":
            session_index = item.data(0, Qt.UserRole + 1)
            mime_data.setText(f"session:{session_index}:{current_folder}")
        else:  # folder
            folder_name = item.data(0, Qt.UserRole + 1)
            mime_data.setText(f"folder:{folder_name}")
            
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)
        
    def dragEnterEvent(self, event):
        """Разрешаем drag enter"""
        if event.mimeData().hasText():
            self._drag_active = True
            self._last_drag_pos = event.pos()
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start()
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """Обработка движения при перетаскивании"""
        if event.mimeData().hasText():
            # Запоминаем последнюю позицию для автопрокрутки
            self._last_drag_pos = event.pos()
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        """Остановка автопрокрутки при выходе из области виджета"""
        self._drag_active = False
        self._last_drag_pos = None
        if self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.stop()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """Обработка drop"""
        if not event.mimeData().hasText():
            return
            
        mime_data = event.mimeData().text()
        target_item = self.itemAt(event.pos())
        
        print(f"Drop event: {mime_data} on {target_item.text(0) if target_item else 'None'}")
        
        # Определяем тип перетаскиваемого элемента
        if mime_data.startswith("session:"):
            self.handle_session_drop(mime_data, target_item)
        elif mime_data.startswith("folder:"):
            folder_name = mime_data.split(":")[1]
            self.handle_folder_drop(folder_name, target_item)
            
        event.acceptProposedAction()
        # Завершаем автопрокрутку
        self._drag_active = False
        self._last_drag_pos = None
        if self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.stop()

    
    def handle_session_drop(self, mime_data, target_item):
        """Обработка drop сессии для вложенных папок"""
        parts = mime_data.split(":")
        session_index = int(parts[1])
        current_folder = parts[2] if len(parts) > 2 else None
        
        print(f"Handling session drop: {session_index} from folder: {current_folder} on {target_item.text(0) if target_item else 'None'}")
        
        if not target_item:
            # Бросили на пустое место - удаляем из папки
            self.session_moved.emit(session_index, None, current_folder)
            return
            
        target_type = target_item.data(0, Qt.UserRole)
        
        if target_type == "folder":
            # Бросили на папку - перемещаем в эту папку
            folder_path = target_item.data(0, Qt.UserRole + 1)
            self.session_moved.emit(session_index, folder_path, current_folder)
        elif target_type == "session":
            # Бросили на сессию - определяем родительскую папку
            parent = target_item.parent()
            if parent and parent.data(0, Qt.UserRole) == "folder":
                # Целевая сессия находится в папке
                folder_path = parent.data(0, Qt.UserRole + 1)
                self.session_moved.emit(session_index, folder_path, current_folder)
            else:
                # Целевая сессия находится в корне - удаляем из папки
                self.session_moved.emit(session_index, None, current_folder)

    def handle_folder_drop(self, folder_name, target_item):
        """Обработка drop папки"""
        # Определяем родителя по месту броска
        target_parent = None
        if target_item:
            target_type = target_item.data(0, Qt.UserRole)
            if target_type == "folder":
                target_parent = target_item.data(0, Qt.UserRole + 1)
            elif target_type == "session":
                parent = target_item.parent()
                if parent and parent.data(0, Qt.UserRole) == "folder":
                    target_parent = parent.data(0, Qt.UserRole + 1)

        # Текущий родитель перемещаемой папки
        parts = folder_name.split('/')
        current_parent = '/'.join(parts[:-1]) if len(parts) > 1 else None

        # Если родитель не меняется — ничего не делаем
        if (current_parent or None) == (target_parent or None):
            return

        # Эмитим сигнал перемещения
        self.folder_moved.emit(folder_name, target_parent)
    
    def _perform_auto_scroll(self):
        """Плавная прокрутка списка при перетаскивании у краев видимой области."""
        if not self._drag_active or self._last_drag_pos is None:
            return
        viewport_rect = self.viewport().rect()
        margin = 24
        vertical_delta = 0
        horizontal_delta = 0

        if self._last_drag_pos.y() < viewport_rect.top() + margin:
            vertical_delta = -20
        elif self._last_drag_pos.y() > viewport_rect.bottom() - margin:
            vertical_delta = 20

        if self._last_drag_pos.x() < viewport_rect.left() + margin:
            horizontal_delta = -20
        elif self._last_drag_pos.x() > viewport_rect.right() - margin:
            horizontal_delta = 20

        if vertical_delta != 0:
            vbar = self.verticalScrollBar()
            vbar.setValue(vbar.value() + vertical_delta)
        if horizontal_delta != 0:
            hbar = self.horizontalScrollBar()
            hbar.setValue(hbar.value() + horizontal_delta)
    
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
                add_subfolder_action = QAction("📁 Add Subfolder", self)
                menu.addAction(add_subfolder_action)
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
                elif action == add_subfolder_action:
                    self.context_menu_requested.emit("add_subfolder", item)
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