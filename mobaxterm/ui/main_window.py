from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QSplitter,
                             QLabel, QPushButton, QMessageBox, QDialog, 
                             QMenu, QAction, QInputDialog,
                             QProgressBar, QLineEdit, QFrame, QApplication,
                             QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QTextCursor, QColor, QFont
from .session_dialog import SessionDialog
from .session_tree_widget import SessionTreeWidget
from ..core.session_manager import SessionManager
from ..core.ssh_client import SSHClient
from ..models.session import Session
import threading
import time
import sys

class SSHThread(QThread):
    output_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.ssh_client = SSHClient()
        
    def run(self):
        self.ssh_client.output_received.connect(self.output_received.emit)
        self.ssh_client.connection_status.connect(self.connection_status.emit)
        self.ssh_client.connect(
            host=self.session.host,
            port=self.session.port,
            username=self.session.username
        )

class MobaXtermClone(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.ssh_thread = None
        self.current_session = None
        self.is_connected = False
        self.folder_items = {}  # folder_name -> QTreeWidgetItem
        self.session_items = {}  # session_index -> QTreeWidgetItem
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('SuperTerminal')
        self.setGeometry(100, 100, 1200, 800)
        
        # Устанавливаем увеличенный шрифт
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top bar with tabs and status
        top_bar = QWidget()
        top_bar.setFixedHeight(35)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(10)
        
        # Tabs
        tabs_widget = QWidget()
        tabs_layout = QHBoxLayout(tabs_widget)
        tabs_layout.setSpacing(2)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        self.session_tab = QPushButton("Session")
        self.session_tab.setCheckable(True)
        self.session_tab.setChecked(True)
        self.session_tab.setFixedSize(80, 30)
        self.session_tab.setStyleSheet(self.get_tab_style(True))
        
        self.servers_tab = QPushButton("Servers")
        self.servers_tab.setCheckable(True)
        self.servers_tab.setFixedSize(80, 30)
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
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: none;
            }
            QTreeWidget::branch:open:has-children {
                image: url(none);
                border-image: none;
            }
            QTreeWidget::branch:closed:has-children {
                image: url(none);
                border-image: none;
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
        
        # Right panel for terminal
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
        
        # Terminal container
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setSpacing(0)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                border: 2px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.terminal_output.setPlainText("")
        
        # Command input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setSpacing(5)
        input_layout.setContentsMargins(0, 4, 0, 0)
        
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 16px;")
        self.prompt_label.setFixedWidth(20)
        
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("""
            QLineEdit {
                background-color: black;
                color: #00ff00;
                border: 2px solid #555;
                border-radius: 2px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }
        """)
        self.command_input.setDisabled(True)
        self.command_input.setPlaceholderText("Type command...")
        self.command_input.returnPressed.connect(self.execute_command)
        
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.command_input)
        
        terminal_layout.addWidget(self.terminal_output)
        terminal_layout.addWidget(input_container)
        right_layout.addWidget(terminal_container)
        
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
        
        # Load saved sessions
        self.load_sessions()
        
    def get_tab_style(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: 2px solid #005fa3;
                    padding: 4px 12px;
                    border-radius: 5px;
                    font-size: 14px;
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
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """

    def on_session_tab_clicked(self):
        self.session_tab.setChecked(True)
        self.servers_tab.setChecked(False)
        self.session_tab.setStyleSheet(self.get_tab_style(True))
        self.servers_tab.setStyleSheet(self.get_tab_style(False))
        
    def on_servers_tab_clicked(self):
        self.servers_tab.setChecked(True)
        self.session_tab.setChecked(False)
        self.servers_tab.setStyleSheet(self.get_tab_style(True))
        self.session_tab.setStyleSheet(self.get_tab_style(False))
        
    def load_sessions(self):
        self.sessions_tree.clear()
        self.folder_items.clear()
        self.session_items.clear()
        
        # Add folders first
        folders = self.session_manager.get_all_folders()
        for folder_name in folders:
            folder_item = QTreeWidgetItem(self.sessions_tree)
            folder_item.setText(0, f"📁 {folder_name}")
            folder_item.setData(0, Qt.UserRole, "folder")
            folder_item.setData(0, Qt.UserRole + 1, folder_name)
            self.folder_items[folder_name] = folder_item
            
            # Add sessions in this folder
            sessions = self.session_manager.get_sessions_in_folder(folder_name)
            for session in sessions:
                session_index = self.session_manager.sessions.index(session)
                self.add_session_to_tree(session, session_index, folder_item)
        
        # Add sessions without folders
        all_session_indices = set(range(len(self.session_manager.sessions)))
        used_indices = set()

        for folder_sessions in self.session_manager.folders.values():
            used_indices.update(folder_sessions)
        
        orphan_sessions = all_session_indices - used_indices
        for session_index in orphan_sessions:
            session = self.session_manager.get_session(session_index)
            if session:  # Добавляем проверку на существование сессии
                session_item = QTreeWidgetItem(self.sessions_tree)
                session_item.setText(0, f"🖥️  {session.host}")
                session_item.setData(0, Qt.UserRole, "session")
                session_item.setData(0, Qt.UserRole + 1, session_index)
                session_item.setToolTip(0, f"{session.type} - {session.host}:{session.port}")
                self.session_items[session_index] = session_item
        
        # Expand all folders by default
        for folder_item in self.folder_items.values():
            folder_item.setExpanded(True)
        
        
    def add_folder_to_list(self, folder_name):
        item = QListWidgetItem(self.sessions_list)
        item.setData(Qt.UserRole, {"type": "folder", "name": folder_name})
        
        folder_widget = FolderItemWidget(folder_name)
        folder_widget.delete_clicked.connect(self.delete_folder_with_confirmation)
        
        self.sessions_list.addItem(item)
        self.sessions_list.setItemWidget(item, folder_widget)
        item.setSizeHint(folder_widget.sizeHint())
        
        self.folder_items[folder_name] = item
        
    def add_session_to_list(self, session, index, folder_name=None):
        item = QListWidgetItem(self.sessions_list)
        
        # Добавляем префикс папки для отображения
        display_name = session.host
        if folder_name:
            display_name = f"{folder_name} / {session.host}"
        
        item.setData(Qt.UserRole, {"type": "session", "index": index, "folder": folder_name})
        
        session_widget = SessionItemWidget(display_name)  # Используем улучшенное имя
        session_widget.delete_clicked.connect(lambda: self.delete_session_with_confirmation(index, session.host))
        
        self.sessions_list.addItem(item)
        self.sessions_list.setItemWidget(item, session_widget)
        item.setSizeHint(session_widget.sizeHint())
        
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
        session_item.setText(0, f"🖥️  {session.host}")
        session_item.setData(0, Qt.UserRole, "session")
        session_item.setData(0, Qt.UserRole + 1, index)
        session_item.setToolTip(0, f"{session.type} - {session.host}:{session.port}")
        self.session_items[index] = session_item

    def handle_tree_context_menu(self, action_type, item):
        if action_type == "add_folder":
            self.add_new_folder()
        elif action_type == "add_session":
            self.add_new_session()
        elif action_type == "add_session_to_folder":
            if item and item.data(0, Qt.UserRole) == "folder":
                folder_name = item.data(0, Qt.UserRole + 1)
                self.add_new_session_to_folder(folder_name)
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
                session = self.session_manager.get_session(session_index)
                if session:
                    self.delete_session_with_confirmation(session_index, session.host)
        elif action_type == "move_session":
            if item and item.data(0, Qt.UserRole) == "session":
                session_index = item.data(0, Qt.UserRole + 1)
                self.move_session_to_folder(session_index)
    def move_session_to_folder(self, session_index):
        session = self.session_manager.get_session(session_index)
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
        
    def update_connection_status(self, connected, message):
        self.hide_loading()
        self.is_connected = connected
        
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
            self.command_input.setDisabled(False)
            self.command_input.setFocus()
        else:
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
            self.command_input.setDisabled(True)
            
        self.connection_info.setText(message)
        self.terminal_output.append(message)
        
    def connect_to_session(self, item):
        if item.data(0, Qt.UserRole) != "session":
            return
            
        if self.is_connected:
            QMessageBox.warning(self, "Warning", "Please disconnect from current session first")
            return
            
        session_index = item.data(0, Qt.UserRole + 1)
        session = self.session_manager.get_session(session_index)
        
        if session and session.type == 'SSH':
            self.current_session = session
            self.show_loading(f"Connecting to {session.host}...")
            self.terminal_output.clear()
            
            self.ssh_thread = SSHThread(session)
            self.ssh_thread.output_received.connect(self.terminal_output.append)
            self.ssh_thread.connection_status.connect(self.update_connection_status)
            self.ssh_thread.start()
    
            
    def execute_command(self):
        if self.is_connected and self.ssh_thread and self.command_input.text():
            command = self.command_input.text()
            self.terminal_output.append(f"$ {command}")
            self.ssh_thread.ssh_client.send_command(command)
            self.command_input.clear()
            
    def show_context_menu(self, position):
        item = self.sessions_list.itemAt(position)
        if not item:
            # Context menu for empty area
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 2px solid #ddd;
                    border-radius: 5px;
                    padding: 6px;
                    font-size: 14px;
                }
                QMenu::item {
                    padding: 6px 24px;
                    font-size: 14px;
                    color: #333;
                }
                QMenu::item:selected {
                    background-color: #e3f2fd;
                    color: #1976d2;
                }
            """)
            
            add_folder_action = QAction("📁 Add Folder", self)
            add_session_action = QAction("➕ Add Session", self)
            
            menu.addAction(add_folder_action)
            menu.addAction(add_session_action)
            
            action = menu.exec_(self.sessions_list.mapToGlobal(position))
            
            if action == add_folder_action:
                self.add_new_folder()
            elif action == add_session_action:
                self.add_new_session()
                
        else:
            item_data = item.data(Qt.UserRole)
            if item_data["type"] == "folder":
                self.show_folder_context_menu(item, position)
            else:
                self.show_session_context_menu(item, position)
    
    def show_folder_context_menu(self, item, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 6px;
                font-size: 14px;
            }
            QMenu::item {
                padding: 6px 24px;
                font-size: 14px;
                color: #333;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        
        delete_action = QAction("🗑️ Delete Folder", self)
        add_session_action = QAction("➕ Add Session to Folder", self)
        
        menu.addAction(add_session_action)
        menu.addAction(delete_action)
        
        action = menu.exec_(self.sessions_list.mapToGlobal(position))
        
        if action == delete_action:
            folder_name = item.data(Qt.UserRole)["name"]
            self.delete_folder_with_confirmation(folder_name)
        elif action == add_session_action:
            folder_name = item.data(Qt.UserRole)["name"]
            self.add_new_session_to_folder(folder_name)
    
    def show_session_context_menu(self, item, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 6px;
                font-size: 14px;
            }
            QMenu::item {
                padding: 6px 24px;
                font-size: 14px;
                color: #333;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        
        delete_action = QAction("🗑️ Delete Session", self)
        edit_action = QAction("✏️ Edit Session", self)
        
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        action = menu.exec_(self.sessions_list.mapToGlobal(position))
        
        if action == delete_action:
            session_index = item.data(Qt.UserRole)["index"]
            session = self.session_manager.get_session(session_index)
            if session:
                self.delete_session_with_confirmation(session_index, session.host)
        elif action == edit_action:
            self.edit_session_item(item)
    
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

    def add_folder_to_tree(self, folder_name):
        folder_item = QTreeWidgetItem(self.sessions_tree)
        folder_item.setText(0, f"📁 {folder_name}")
        folder_item.setData(0, Qt.UserRole, "folder")
        folder_item.setData(0, Qt.UserRole + 1, folder_name)
        folder_item.setToolTip(0, f"Folder: {folder_name}")
        folder_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        folder_item.setExpanded(True)
        self.folder_items[folder_name] = folder_item
        return folder_item

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
                # Удаляем из дерева
                if folder_name in self.folder_items:
                    folder_item = self.folder_items[folder_name]
                    self.sessions_tree.takeTopLevelItem(self.sessions_tree.indexOfTopLevelItem(folder_item))
                    del self.folder_items[folder_name]
    
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
            
            self.add_session_to_tree(session, session_index, folder_item)

    def edit_session(self, session_index):
        session = self.session_manager.get_session(session_index)
        if session:
            dialog = SessionDialog(self, session)
            if dialog.exec_() == QDialog.Accepted:
                updated_session = dialog.get_session_data()
                if self.session_manager.update_session(session_index, updated_session):
                    # Перезагружаем дерево для отображения изменений
                    self.load_sessions()
    def edit_session_item(self, item):
        item_data = item.data(Qt.UserRole)
        if item_data["type"] != "session":
            return
            
        session_index = item_data["index"]
        session = self.session_manager.get_session(session_index)
        
        if session:
            dialog = SessionDialog(self, session)
            if dialog.exec_() == QDialog.Accepted:
                updated_session = dialog.get_session_data()
                if self.session_manager.update_session(session_index, updated_session):
                    # Update the widget text
                    widget = self.sessions_list.itemWidget(item)
                    if widget:
                        widget.name_label.setText(updated_session.host)
                    # Reload to handle folder changes
                    self.load_sessions()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MobaXtermClone()
    window.show()
    sys.exit(app.exec_())