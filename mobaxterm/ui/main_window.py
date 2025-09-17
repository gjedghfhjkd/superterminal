from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter,
                             QLabel, QPushButton, QMessageBox, QDialog, 
                             QMenu, QAction, QInputDialog, QLineEdit,
                             QProgressBar, QFrame, QApplication,
                             QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QTextCursor, QColor, QFont
from .session_dialog import SessionDialog
from .session_tree_widget import SessionTreeWidget
from .terminal_tabs import TerminalTabs
from .terminal2 import Terminal2
from .terminal_js import TerminalJS
from ..core.session_manager import SessionManager
from ..core.ssh2 import SSH2
from ..core.sftp_client import SFTPClient
from .sftp_tab import SFTPTab
from ..models.session import Session
from .tunneling_dialog import TunnelingDialog
import threading
import time
import sys

class SSHThread(QThread):
    output_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)
    input_to_send = pyqtSignal(str)
    
    def __init__(self, session, terminal_tab):
        super().__init__()
        self.session = session
        self.terminal_tab = terminal_tab
        self.ssh_client = None
    
    def send_raw(self, data: str):
        # This method can be called from UI thread; it emits a signal that
        # will be delivered to the SSH client within this QThread context.
        self.input_to_send.emit(data)

    def run(self):
        self.ssh_client = SSH2()
        # Route output to UI
        self.ssh_client.output_received.connect(self.terminal_tab.append_output)
        self.ssh_client.connection_status.connect(self.connection_status.emit)
        # Deliver input in thread context
        self.input_to_send.connect(self.ssh_client.send)
        self.ssh_client.connect(
            host=self.session.host,
            port=self.session.port,
            username=self.session.username,
            auth_method=getattr(self.session, 'auth_method', 'password'),
            key_filename=getattr(self.session, 'private_key_path', None),
            passphrase=getattr(self.session, 'private_key_passphrase', None),
            allow_agent=True,
            look_for_keys=True
        )
        # Start event loop so queued signals (input_to_send) are processed in this thread
        self.exec_()

class SFTPThread(QThread):
    connection_status = pyqtSignal(bool, str)
    remote_listing = pyqtSignal(str, list)
    change_dir = pyqtSignal(str)
    up_dir = pyqtSignal()
    upload_files = pyqtSignal(list, str)
    download_files = pyqtSignal(list, str)
    delete_paths = pyqtSignal(list)
    rename_path = pyqtSignal(str, str)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.client = None

    def run(self):
        self.client = SFTPClient()
        self.client.connection_status.connect(self.connection_status.emit)
        self.client.remote_listing.connect(self.remote_listing.emit)
        # UI -> thread operations
        self.change_dir.connect(self.client.change_dir)
        self.up_dir.connect(self.client.up_dir)
        self.upload_files.connect(self.client.upload_files)
        self.download_files.connect(self.client.download_files)
        self.delete_paths.connect(self.client.delete_paths)
        self.rename_path.connect(self.client.rename_path)
        # Connect now
        self.client.connect(
            host=self.session.host,
            port=self.session.port,
            username=self.session.username,
            password=getattr(self.session, 'password', None),
            auth_method=getattr(self.session, 'auth_method', 'password'),
            key_filename=getattr(self.session, 'private_key_path', None),
            passphrase=getattr(self.session, 'private_key_passphrase', None),
            allow_agent=True,
            look_for_keys=True
        )
        self.exec_()

    def disconnect(self):
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass

    # Wrapper slots to forward calls via signals (queued to this thread)
    def on_change_dir(self, path: str):
        try:
            self.change_dir.emit(path)
        except Exception:
            pass

    def on_up_dir(self):
        try:
            self.up_dir.emit()
        except Exception:
            pass

    def on_upload(self, local_paths: list, remote_dir: str):
        try:
            self.upload_files.emit(local_paths, remote_dir)
        except Exception:
            pass

    def on_download(self, remote_paths: list, local_dir: str):
        try:
            self.download_files.emit(remote_paths, local_dir)
        except Exception:
            pass

    def on_delete(self, remote_paths: list):
        try:
            self.delete_paths.emit(remote_paths)
        except Exception:
            pass

    def on_rename(self, old_path: str, new_basename: str):
        try:
            self.rename_path.emit(old_path, new_basename)
        except Exception:
            pass

class MobaXtermClone(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.ssh_threads = {}  # session_index -> SSHThread
        self.current_session_index = None
        self.is_connected = False
        self.folder_items = {}
        self.session_items = {}
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('SuperTerminal')
        self.setGeometry(100, 100, 1200, 800)
        
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top bar with tabs and status
        top_bar = QWidget()
        top_bar.setFixedHeight(40)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(10)
        
        # Tabs
        tabs_widget = QWidget()
        tabs_layout = QHBoxLayout(tabs_widget)
        tabs_layout.setSpacing(2)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        self.session_tab = QPushButton("🗂 Sessions")
        self.session_tab.setCheckable(True)
        self.session_tab.setChecked(False)
        self.session_tab.setFixedSize(130, 34)
        self.session_tab.setStyleSheet(self.get_tab_style(False))
        
        self.servers_tab = QPushButton("📡 Tunelling")
        self.servers_tab.setCheckable(True)
        self.servers_tab.setFixedSize(110, 34)
        self.servers_tab.setStyleSheet(self.get_tab_style(False))
        
        tabs_layout.addWidget(self.session_tab)
        tabs_layout.addWidget(self.servers_tab)
        tabs_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(18, 18)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #dc3545;
                color: white;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                padding: 2px;
            }
        """)
        self.status_label.setFixedWidth(100)
        
        top_bar_layout.addWidget(tabs_widget)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.status_indicator)
        top_bar_layout.addWidget(self.status_label)
        
        main_layout.addWidget(top_bar)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #ddd;")
        separator.setFixedHeight(2)
        main_layout.addWidget(separator)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel for sessions tree
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(5)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sessions label
        sessions_header = QWidget()
        sessions_header_layout = QHBoxLayout(sessions_header)
        sessions_header_layout.setContentsMargins(0, 0, 0, 0)
        
        sessions_title = QLabel("Sessions")
        sessions_title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                font-size: 16px;
            }
        """)
        
        sessions_header_layout.addWidget(sessions_title)
        sessions_header_layout.addStretch()
        
        left_layout.addWidget(sessions_header)
        
        # Sessions tree
        self.sessions_tree = SessionTreeWidget()
        self.sessions_tree.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 8px;
                height: 32px;
                border: 1px solid transparent;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
                border: 1px solid #bbdefb;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #f5f9ff;
                border: 1px solid #cce5ff;
            }
            QTreeWidget::item:selected:hover {
                background-color: #d1e7ff;
                border: 1px solid #90caf9;
            }
            QTreeWidget::item[dragging="true"] {
                background-color: #fff3cd;
                border: 1px dashed #ffc107;
            }
        """)
        left_layout.addWidget(self.sessions_tree)
        
        # Add session button
        self.add_session_btn = QPushButton("+ Add Session")
        self.add_session_btn.setFixedHeight(35)
        self.add_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 2px solid #dee2e6;
                padding: 6px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #ced4da;
            }
        """)
        self.add_session_btn.clicked.connect(self.add_new_session)
        left_layout.addWidget(self.add_session_btn)
        
        # Right panel for terminal tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(5)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #f0f0f0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 2px;
            }
        """)
        right_layout.addWidget(self.progress_bar)
        
        # Terminal tabs
        self.terminal_tabs = TerminalTabs()
        self.terminal_tabs.tab_close_requested.connect(self.close_terminal_tab)
        right_layout.addWidget(self.terminal_tabs)
        
        # Bottom status bar
        bottom_status = QWidget()
        bottom_status.setFixedHeight(30)
        bottom_status_layout = QHBoxLayout(bottom_status)
        bottom_status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.connection_info = QLabel("Ready to connect")
        self.connection_info.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 2px;
                background-color: #f8f9fa;
                border-radius: 2px;
            }
        """)
        
        bottom_status_layout.addWidget(self.connection_info)
        bottom_status_layout.addStretch()
        
        right_layout.addWidget(bottom_status)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        
        content_layout.addWidget(splitter)
        main_layout.addWidget(content_widget)
        
        # Connect signals
        self.session_tab.clicked.connect(self.on_session_tab_clicked)
        self.servers_tab.clicked.connect(self.on_servers_tab_clicked)
        self.sessions_tree.session_double_clicked.connect(self.connect_to_session)
        self.sessions_tree.context_menu_requested.connect(self.handle_tree_context_menu)
        self.sessions_tree.rename_requested.connect(self.handle_rename_request)
        self.sessions_tree.session_moved.connect(self.handle_session_move)
        self.sessions_tree.folder_moved.connect(self.handle_folder_move)

        
        # Load saved sessions
        self.load_sessions()

    def handle_session_move(self, session_index, target_folder, current_folder):
        """Обработка перемещения сессии"""
        print(f"Moving session {session_index} from folder: {current_folder} to folder: {target_folder}")
        
        session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
        if not session:
            print("Session not found!")
            return
            
        print(f"Session current folder in DB: {session.folder}")
        print(f"Source folder (from drag): {current_folder}")
        print(f"Target folder: {target_folder}")
        
        # Проверяем, действительно ли папка изменилась
        # Сравниваем исходную папку (из которой перемещаем) с целевой папкой
        if current_folder == target_folder:
            print("Session is already in the target folder - no need to move")
            return
            
        # Обновляем папку сессии
        session.folder = target_folder
        if self.session_manager.update_session(session_index, session):
            print("Session updated successfully")
            # Перезагружаем дерево для отображения изменений
            self.load_sessions()
        else:
            print("Failed to update session")

    def handle_folder_move(self, folder_path, target_parent):
        """Обработка перемещения папки"""
        # Валидация на уровне UI (дополнительно к бэкенду)
        if target_parent and (target_parent == folder_path or target_parent.startswith(folder_path + '/')):
            QMessageBox.warning(self, "Invalid Move", "Cannot move a folder into itself or its descendant.")
            return

        if not self.session_manager.move_folder(folder_path, target_parent):
            QMessageBox.warning(self, "Move Failed", "Could not move folder. It may already exist at destination or the move is invalid.")
            return

        # Успех — перезагружаем дерево
        self.load_sessions()

    def handle_rename_request(self, item_type, item):
        """Обработка запроса на переименование"""
        if item_type == "folder":
            folder_name = item.data(0, Qt.UserRole + 1)
            self.rename_folder(folder_name, item)
        elif item_type == "session":
            session_index = item.data(0, Qt.UserRole + 1)
            session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
            if session:
                self.rename_session(session_index, session, item)
    def rename_session(self, session_index, session, item):
        """Переименование сессии (меняет только Session Name, не Remote host)"""
        current_display_name = session.name or session.host
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Session",
            "Enter new session name:",
            QLineEdit.Normal,
            current_display_name
        )
        
        if ok and new_name and new_name != current_display_name:
            session.name = new_name
            if self.session_manager.update_session(session_index, session):
                # Обновляем отображение: показываем Session Name, tooltip оставляем с host:port
                icon = "🖥️" if session.type == 'SSH' else "🔗"
                user_suffix = f" ({session.username})" if getattr(session, 'username', None) else ""
                item.setText(0, f"{icon}  {session.name}{user_suffix}")
                item.setToolTip(0, f"{session.type} - {session.host}:{session.port}")
    
    def rename_folder(self, old_folder_name, item):
        """Переименование папки"""
        new_folder_name, ok = QInputDialog.getText(
            self,
            "Rename Folder",
            "Enter new folder name:",
            QLineEdit.Normal,
            old_folder_name
        )
        
        if ok and new_folder_name and new_folder_name != old_folder_name:
            if self.session_manager.rename_folder(old_folder_name, new_folder_name):
                # Обновляем отображение
                item.setText(0, f"📁 {new_folder_name}")
                item.setData(0, Qt.UserRole + 1, new_folder_name)
                
                # Обновляем словарь folder_items
                if old_folder_name in self.folder_items:
                    self.folder_items[new_folder_name] = self.folder_items.pop(old_folder_name)
    def get_tab_style(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: 2px solid #005fa3;
                    padding: 4px 12px;
                    border-radius: 5px;
                    font-size: 15px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f8f9fa;
                    color: #495057;
                    border: 2px solid #dee2e6;
                    padding: 4px 12px;
                    border-radius: 5px;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """
        
    def on_session_tab_clicked(self):
        # Keep both tabs in neutral style after click
        self.session_tab.setChecked(False)
        self.servers_tab.setChecked(False)
        self.session_tab.setStyleSheet(self.get_tab_style(False))
        self.servers_tab.setStyleSheet(self.get_tab_style(False))
        # Open the same dialog as "+ Add Session"
        try:
            self.add_new_session()
        except Exception:
            pass
        
    def on_servers_tab_clicked(self):
        # Keep both tabs in neutral style after click
        self.session_tab.setChecked(False)
        self.servers_tab.setChecked(False)
        self.session_tab.setStyleSheet(self.get_tab_style(False))
        self.servers_tab.setStyleSheet(self.get_tab_style(False))
        self.open_tunnelling_dialog()
        
    def load_sessions(self):
        """Загрузка сессий с поддержкой вложенных папок"""
        self.sessions_tree.clear()
        self.folder_items.clear()
        self.session_items.clear()
        
        # Создаем (и отображаем) все папки, включая вложенные
        all_folders = self.session_manager.get_all_folders()
        for folder_path in all_folders:
            if folder_path:
                self.add_folder_to_tree(folder_path)
        
        # Добавляем сессии в соответствующие папки или в корень
        for index, session in enumerate(self.session_manager.get_all_sessions()):
            if session.folder:
                folder_item = self.folder_items.get(session.folder)
                if not folder_item:
                    folder_item = self.add_folder_to_tree(session.folder)
                parent_item = folder_item if folder_item else self.sessions_tree
                self.add_session_to_tree(session, index, parent_item)
            else:
                self.add_session_to_tree(session, index, self.sessions_tree)
        
    def handle_tree_context_menu(self, action_type, item):
        if action_type == "add_folder":
            self.add_new_folder()
        elif action_type == "add_session":
            self.add_new_session()
        elif action_type == "add_session_to_folder":
            if item and item.data(0, Qt.UserRole) == "folder":
                folder_name = item.data(0, Qt.UserRole + 1)
                self.add_new_session_to_folder(folder_name)
        elif action_type == "add_subfolder":
            if item and item.data(0, Qt.UserRole) == "folder":
                parent_folder = item.data(0, Qt.UserRole + 1)
                sub_name, ok = QInputDialog.getText(
                    self,
                    "New Subfolder",
                    f"Enter subfolder name under '{parent_folder}':",
                    QLineEdit.Normal
                )
                if ok and sub_name:
                    new_path = f"{parent_folder}/{sub_name}"
                    if self.session_manager.add_folder(new_path):
                        self.load_sessions()
        elif action_type == "delete_folder":
            if item and item.data(0, Qt.UserRole) == "folder":
                folder_name = item.data(0, Qt.UserRole + 1)
                self.delete_folder_with_confirmation(folder_name)
        elif action_type == "edit_session":
            if item and item.data(0, Qt.UserRole) == "session":
                session_index = item.data(0, Qt.UserRole + 1)
                self.edit_session(session_index)
        elif action_type == "delete_session":
            if item and item.data(0, Qt.UserRole) == "session":
                session_index = item.data(0, Qt.UserRole + 1)
                session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
                if session:
                    self.delete_session_with_confirmation(session_index, session.host)
        elif action_type == "move_session":
            if item and item.data(0, Qt.UserRole) == "session":
                session_index = item.data(0, Qt.UserRole + 1)
                self.move_session_to_folder(session_index)
    def keyPressEvent(self, event):
        # Глобальная обработка F2 и Delete
        if event.key() == Qt.Key_F2 or event.key() == Qt.Key_Delete:
            # Передаем событие дереву сессий, если оно в фокусе
            if self.sessions_tree.hasFocus():
                # Дерево само обработает эти клавиши
                event.ignore()  # Позволяем дереву обработать событие
                return
                
        super().keyPressEvent(event)
    def add_new_session(self, folder_name=None):
        dialog = SessionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            session = dialog.get_session_data()
            # Если папка указана в диалоге, используем ее
            target_folder = session.folder or folder_name
            session_index = self.session_manager.add_session(session, target_folder)
            
            if target_folder:
                # Добавляем в папку
                if target_folder in self.folder_items:
                    folder_item = self.folder_items[target_folder]
                else:
                    folder_item = self.add_folder_to_tree(target_folder)
                self.add_session_to_tree(session, session_index, folder_item)
            else:
                # Добавляем в корень
                self.add_session_to_tree(session, session_index, self.sessions_tree)
    
    def add_session_to_tree(self, session, index, parent_item):
        session_item = QTreeWidgetItem(parent_item)
        display_name = (getattr(session, 'name', None) or session.host)
        if getattr(session, 'username', None):
            display_name = f"{display_name} ({session.username})"
        icon = "🖥️" if session.type == 'SSH' else "🔗"
        session_item.setText(0, f"{icon}  {display_name}")
        session_item.setData(0, Qt.UserRole, "session")
        session_item.setData(0, Qt.UserRole + 1, index)
        session_item.setToolTip(0, f"{session.type} - {session.host}:{session.port}")
        self.session_items[index] = session_item
        
    def add_folder_to_tree(self, folder_name):
        # Создаем вложенные элементы для пути вида "parent/child/sub"
        parts = folder_name.split('/') if folder_name else []
        parent_item = None
        built_parts = []
        for part in parts:
            built_parts.append(part)
            current_path = '/'.join(built_parts)
            if current_path in self.folder_items:
                parent_item = self.folder_items[current_path]
                continue
            container = parent_item if parent_item else self.sessions_tree
            folder_item = QTreeWidgetItem(container)
            folder_item.setText(0, f"📁 {part}")
            folder_item.setData(0, Qt.UserRole, "folder")
            folder_item.setData(0, Qt.UserRole + 1, current_path)
            folder_item.setToolTip(0, f"Folder: {current_path}")
            folder_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            folder_item.setExpanded(True)
            self.folder_items[current_path] = folder_item
            parent_item = folder_item
        return self.folder_items.get(folder_name)
    
    def add_new_session_to_folder(self, folder_name):
        dialog = SessionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            session = dialog.get_session_data()
            # Принудительно устанавливаем папку
            session.folder = folder_name
            session_index = self.session_manager.add_session(session, folder_name)
            
            if folder_name in self.folder_items:
                folder_item = self.folder_items[folder_name]
            else:
                folder_item = self.add_folder_to_tree(folder_name)
            
            session_item = QTreeWidgetItem(folder_item)
            display_name = (getattr(session, 'name', None) or session.host)
            if getattr(session, 'username', None):
                display_name = f"{display_name} ({session.username})"
            icon = "🖥️" if session.type == 'SSH' else "🔗"
            session_item.setText(0, f"{icon}  {display_name}")
            session_item.setData(0, Qt.UserRole, "session")
            session_item.setData(0, Qt.UserRole + 1, session_index)
            session_item.setToolTip(0, f"{session.type} - {session.host}:{session.port}")
            self.session_items[session_index] = session_item
    
    def add_new_folder(self):
        folder_name, ok = QInputDialog.getText(
            self, 
            "New Folder", 
            "Enter folder name:",
            QLineEdit.Normal
        )
        
        if ok and folder_name:
            if self.session_manager.add_folder(folder_name):
                self.add_folder_to_tree(folder_name)
    
    def delete_folder_with_confirmation(self, folder_name):
        # Получаем сессии в папке
        sessions_in_folder = self.session_manager.get_sessions_in_folder(folder_name)
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete folder '{folder_name}'?\n"
            f"It contains {len(sessions_in_folder)} session(s).\n\n"
            "All sessions in this folder will also be deleted!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Удаляем все сессии в папке
            for session in sessions_in_folder:
                session_index = self.session_manager.sessions.index(session)
                self.session_manager.delete_session(session_index)
            
            # Удаляем саму папку
            if self.session_manager.delete_folder(folder_name):
                # Перезагружаем дерево, чтобы отразить изменения немедленно
                self.load_sessions()
    
    def delete_session_with_confirmation(self, session_index, session_name):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete session:\n{session_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.session_manager.delete_session(session_index):
                # Перезагружаем дерево
                self.load_sessions()
    
    def edit_session(self, session_index):
        session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
        if session:
            dialog = SessionDialog(self, session)
            if dialog.exec_() == QDialog.Accepted:
                updated_session = dialog.get_session_data()
                if self.session_manager.update_session(session_index, updated_session):
                    # Перезагружаем дерево для отображения изменений
                    self.load_sessions()
    
    def move_session_to_folder(self, session_index):
        session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
        if not session:
            return
        
        # Получаем список всех папок
        folders = self.session_manager.get_all_folders()
        
        # Создаем диалог для выбора папки
        folder_name, ok = QInputDialog.getItem(
            self,
            "Move Session",
            f"Select folder for session '{session.host}':",
            ["(No folder)"] + folders,
            0,  # default index
            False  # not editable
        )
        
        if ok:
            target_folder = folder_name if folder_name != "(No folder)" else None
            
            # Обновляем сессию
            session.folder = target_folder
            if self.session_manager.update_session(session_index, session):
                # Перезагружаем дерево
                self.load_sessions()
    
    def connect_to_session(self, item):
        if item.data(0, Qt.UserRole) != "session":
            return
            
        session_index = item.data(0, Qt.UserRole + 1)
        session = self.session_manager.sessions[session_index] if session_index < len(self.session_manager.sessions) else None
        
        if session and session.type == 'SSH':
            # Проверяем, не подключены ли мы уже к этой сессии
            if session_index in self.ssh_threads:
                # Переключаемся на существующую вкладку
                for i in range(self.terminal_tabs.count()):
                    tab = self.terminal_tabs.widget(i)
                    if hasattr(tab, 'session_index') and tab.session_index == session_index:
                        self.terminal_tabs.setCurrentIndex(i)
                        return
                return
            
            self.current_session_index = session_index
            self.show_loading(f"Connecting to {session.host}...")
            
            # Создаем новую вкладку терминала
            # Choose terminal implementation via feature flag
            if getattr(session, 'use_terminal2', False):
                # Prefer JS terminal if available for better full-screen app support
                try:
                    terminal_widget = TerminalJS()
                except Exception:
                    terminal_widget = Terminal2()
                # Add as a tab with display name
                display_name = getattr(session, 'name', None) or session.host
                tab_index = self.terminal_tabs.addTab(terminal_widget, f"🖥️ {display_name}")
                # Add close button to this Terminal2 tab as well
                try:
                    self.terminal_tabs._add_close_button_to_tab(tab_index)
                except Exception:
                    pass
                self.terminal_tabs.setCurrentIndex(tab_index)
                terminal_tab = terminal_widget
            else:
                terminal_tab = self.terminal_tabs.add_terminal_tab(session)
            terminal_tab.session_index = session_index
            terminal_tab.command_submitted.connect(
                lambda cmd, idx=session_index: self.execute_command(idx, cmd)
            )
            
            # Создаем и запускаем SSH поток
            ssh_thread = SSHThread(session, terminal_tab)
            ssh_thread.connection_status.connect(
                lambda status, msg: self.update_connection_status(session_index, status, msg)
            )
            ssh_thread.start()
            
            self.ssh_threads[session_index] = ssh_thread

            # Provide terminal with a way to send raw keys to this SSH thread
            # Wire sender depending on terminal type
            try:
                if hasattr(terminal_tab, 'set_key_sender'):
                    terminal_tab.set_key_sender(lambda data, t=ssh_thread: t.send_raw(data))
                elif hasattr(terminal_tab, 'set_sender'):
                    terminal_tab.set_sender(lambda data, t=ssh_thread: t.send_raw(data))
            except Exception:
                pass

            # If the user starts typing immediately, ensure input is enabled
            try:
                if hasattr(terminal_tab, 'enable_input'):
                    terminal_tab.enable_input()
                else:
                    terminal_tab.view.setReadOnly(False)
                    terminal_tab.view.setFocus()
            except Exception:
                pass
        elif session and session.type == 'SFTP':
            # Check existing SFTP tab
            if session_index in getattr(self, 'sftp_threads', {}):
                for i in range(self.terminal_tabs.count()):
                    tab = self.terminal_tabs.widget(i)
                    if hasattr(tab, 'session_index') and tab.session_index == session_index:
                        self.terminal_tabs.setCurrentIndex(i)
                        return
                return

            self.current_session_index = session_index
            self.show_loading(f"Connecting (SFTP) to {session.host}...")

            # Create SFTP tab UI
            sftp_tab = SFTPTab(session)
            sftp_tab.session_index = session_index

            # Start SFTP thread
            sftp_thread = SFTPThread(session)
            # Wire UI -> thread navigation via wrapper slots to ensure queued delivery
            sftp_tab.remote_change_dir.connect(sftp_thread.on_change_dir)
            sftp_tab.remote_up_dir.connect(sftp_thread.on_up_dir)
            sftp_tab.request_upload.connect(sftp_thread.on_upload)
            sftp_tab.request_download.connect(sftp_thread.on_download)
            sftp_tab.request_remote_delete.connect(sftp_thread.on_delete)
            sftp_tab.request_remote_rename.connect(sftp_thread.on_rename)
            # Wire thread -> UI
            sftp_thread.remote_listing.connect(sftp_tab.set_remote_listing)
            sftp_thread.connection_status.connect(
                lambda status, msg: self.update_connection_status(session_index, status, msg)
            )

            sftp_thread.start()

            # Lazily create dict to track SFTP threads
            if not hasattr(self, 'sftp_threads'):
                self.sftp_threads = {}
            self.sftp_threads[session_index] = sftp_thread

            # Add tab to UI
            self.terminal_tabs.add_sftp_tab(session, sftp_tab)
    
    def execute_command(self, session_index, command: str):
        if session_index in self.ssh_threads and command is not None:
            ssh_thread = self.ssh_threads[session_index]
            terminal_tab = self.terminal_tabs.get_current_terminal()
            if terminal_tab:
                # Command line is already visible inline in the terminal widget
                ssh_thread.ssh_client.send_command(command)
    
    def update_connection_status(self, session_index, connected, message):
        self.hide_loading()
        
        if connected:
            self.status_indicator.setStyleSheet("""
                QLabel {
                    background-color: #28a745;
                    color: white;
                    border-radius: 9px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            self.status_label.setText("Connected")
            
            # Включаем ввод для текущей вкладки
            terminal_tab = self.terminal_tabs.get_current_terminal()
            if terminal_tab:
                terminal_tab.enable_input()
        else:
            if not any(thread.isRunning() for thread in self.ssh_threads.values()):
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        background-color: #dc3545;
                        color: white;
                        border-radius: 9px;
                        font-size: 10px;
                        font-weight: bold;
                    }
                """)
                self.status_label.setText("Disconnected")
            
        self.connection_info.setText(message)
        # Не печатаем статусные сообщения в терминал, только в статус-бар
    
    def close_terminal_tab(self, index):
        tab = self.terminal_tabs.widget(index)
        if hasattr(tab, 'session_index'):
            session_index = tab.session_index
            if session_index in self.ssh_threads:
                # Отключаем SSH соединение
                ssh_thread = self.ssh_threads[session_index]
                if ssh_thread.isRunning():
                    ssh_thread.ssh_client.disconnect()
                    ssh_thread.quit()
                    ssh_thread.wait()
                del self.ssh_threads[session_index]
            # SFTP cleanup
            if hasattr(self, 'sftp_threads') and session_index in self.sftp_threads:
                sftp_thread = self.sftp_threads[session_index]
                if sftp_thread.isRunning():
                    sftp_thread.disconnect()
                    sftp_thread.quit()
                    sftp_thread.wait()
                del self.sftp_threads[session_index]
        
        self.terminal_tabs.removeTab(index)
        
        # Если закрыли все вкладки, обновляем статус
        if self.terminal_tabs.count() == 0:
            self.status_indicator.setStyleSheet("""
                QLabel {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 9px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            self.status_label.setText("Disconnected")
            self.connection_info.setText("Ready to connect")
    
    def show_loading(self, message="Connecting..."):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #ffc107;
                color: white;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.status_label.setText("Connecting...")
        self.connection_info.setText(f"⏳ {message}")
        
    def hide_loading(self):
        self.progress_bar.setVisible(False)

    def open_tunnelling_dialog(self):
        try:
            dlg = TunnelingDialog(self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Tunnelling", f"Failed to open tunnelling manager: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MobaXtermClone()
    window.show()
    sys.exit(app.exec_())