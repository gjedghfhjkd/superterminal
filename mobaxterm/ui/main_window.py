from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QTextEdit, QSplitter,
                             QLabel, QPushButton, QMessageBox, QDialog, 
                             QListWidgetItem, QMenu, QAction, QInputDialog,
                             QProgressBar, QLineEdit, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QTextCursor, QColor, QFont
from .session_dialog import SessionDialog
from ..core.session_manager import SessionManager
from ..core.ssh_client import SSHClient
from ..models.session import Session
import threading
import time

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
        self.initUI()
        
    # ... (предыдущий код остается без изменений)

    def initUI(self):
        self.setWindowTitle('SuperTerminal')
        self.setGeometry(100, 100, 1000, 600)  # Уменьшаем общий размер окна
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(3)  # Уменьшаем отступы
        main_layout.setContentsMargins(3, 3, 3, 3)  # Уменьшаем поля
        
        # Top bar with tabs and status - делаем более компактным
        top_bar = QWidget()
        top_bar.setFixedHeight(25)  # Фиксируем высоту
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(5)
        
        # Tabs - уменьшаем размер
        tabs_widget = QWidget()
        tabs_layout = QHBoxLayout(tabs_widget)
        tabs_layout.setSpacing(1)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        self.session_tab = QPushButton("Session")
        self.session_tab.setCheckable(True)
        self.session_tab.setChecked(True)
        self.session_tab.setFixedSize(60, 20)  # Уменьшаем размер
        self.session_tab.setStyleSheet(self.get_tab_style(True))
        
        self.servers_tab = QPushButton("Servers")
        self.servers_tab.setCheckable(True)
        self.servers_tab.setFixedSize(60, 20)  # Уменьшаем размер
        self.servers_tab.setStyleSheet(self.get_tab_style(False))
        
        tabs_layout.addWidget(self.session_tab)
        tabs_layout.addWidget(self.servers_tab)
        tabs_layout.addStretch()
        
        # Status indicator - делаем меньше
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #dc3545;
                color: white;
                border-radius: 6px;
                font-size: 6px;
                font-weight: bold;
            }
        """)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding: 1px;
            }
        """)
        self.status_label.setFixedWidth(80)  # Уменьшаем ширину
        
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
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(5)  # Уменьшаем отступы
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel for sessions - уменьшаем ширину
        left_panel = QWidget()
        left_panel.setFixedWidth(180)  # Уменьшаем ширину с 250 до 180
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(3)  # Уменьшаем отступы
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sessions label - уменьшаем шрифт
        sessions_header = QWidget()
        sessions_header_layout = QHBoxLayout(sessions_header)
        sessions_header_layout.setContentsMargins(0, 0, 0, 0)
        
        sessions_title = QLabel("Sessions")
        sessions_title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                font-size: 11px;  # Уменьшаем шрифт
            }
        """)
        
        sessions_header_layout.addWidget(sessions_title)
        sessions_header_layout.addStretch()
        
        left_layout.addWidget(sessions_header)
        
        # Sessions list - уменьшаем отступы и шрифт
        self.sessions_list = QListWidget()
        self.sessions_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 2px;
                font-size: 10px;  # Уменьшаем шрифт
            }
            QListWidget::item {
                padding: 4px 6px;  # Уменьшаем отступы
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                border: 1px solid #bbdefb;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.sessions_list.setContextMenuPolicy(Qt.CustomContextMenu)
        left_layout.addWidget(self.sessions_list)
        
        # Add session button - уменьшаем размер
        self.add_session_btn = QPushButton("+ Add Session")
        self.add_session_btn.setFixedHeight(25)  # Фиксируем высоту
        self.add_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                padding: 4px;
                border-radius: 2px;
                font-size: 10px;  # Уменьшаем шрифт
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
        right_layout.setSpacing(3)  # Уменьшаем отступы
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(2)  # Уменьшаем высоту
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #f0f0f0;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 1px;
            }
        """)
        right_layout.addWidget(self.progress_bar)
        
        # Terminal container
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setSpacing(0)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Terminal output - уменьшаем шрифт
        self.terminal_output = QTextEdit()
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;  # Уменьшаем шрифт
                border: 1px solid #ccc;
                border-radius: 2px;
                padding: 3px;
            }
        """)
        self.terminal_output.setPlainText("")
        
        # Command input area - уменьшаем отступы
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setSpacing(3)
        input_layout.setContentsMargins(0, 2, 0, 0)
        
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 10px;")
        self.prompt_label.setFixedWidth(12)
        
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("""
            QLineEdit {
                background-color: black;
                color: #00ff00;
                border: 1px solid #555;
                border-radius: 1px;
                padding: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;  # Уменьшаем шрифт
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
        
        # Bottom status bar - уменьшаем высоту
        bottom_status = QWidget()
        bottom_status.setFixedHeight(20)
        bottom_status_layout = QHBoxLayout(bottom_status)
        bottom_status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.connection_info = QLabel("Ready to connect")
        self.connection_info.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 9px;  # Уменьшаем шрифт
                padding: 1px;
                background-color: #f8f9fa;
                border-radius: 1px;
            }
        """)
        
        bottom_status_layout.addWidget(self.connection_info)
        bottom_status_layout.addStretch()
        
        right_layout.addWidget(bottom_status)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([180, 820])  # Обновляем размеры
        
        content_layout.addWidget(splitter)
        main_layout.addWidget(content_widget)
        
        # Connect signals
        self.session_tab.clicked.connect(self.on_session_tab_clicked)
        self.servers_tab.clicked.connect(self.on_servers_tab_clicked)
        self.sessions_list.itemDoubleClicked.connect(self.connect_to_session)
        self.sessions_list.customContextMenuRequested.connect(self.show_context_menu)
        
        # Load saved sessions
        self.load_sessions()

    # ... (остальной код остается без изменений)
        
    def get_tab_style(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: 1px solid #005fa3;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f8f9fa;
                    color: #495057;
                    border: 1px solid #dee2e6;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 11px;
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
        self.sessions_list.clear()
        sessions = self.session_manager.get_all_sessions()
        for i, session in enumerate(sessions):
            item = QListWidgetItem(session.host)
            item.setData(Qt.UserRole, i)
            self.sessions_list.addItem(item)
        
    def add_new_session(self):
        dialog = SessionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            session = dialog.get_session_data()
            session_index = self.session_manager.add_session(session)
            item = QListWidgetItem(session.host)
            item.setData(Qt.UserRole, session_index)
            self.sessions_list.addItem(item)
            
    def show_loading(self, message="Connecting..."):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #ffc107;
                color: white;
                border-radius: 8px;
                font-size: 8px;
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
                    border-radius: 8px;
                    font-size: 8px;
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
                    border-radius: 8px;
                    font-size: 8px;
                    font-weight: bold;
                }
            """)
            self.status_label.setText("Disconnected")
            self.command_input.setDisabled(True)
            
        self.connection_info.setText(message)
        self.terminal_output.append(message)
        
    def connect_to_session(self, item):
        if self.is_connected:
            QMessageBox.warning(self, "Warning", "Please disconnect from current session first")
            return
            
        session_index = item.data(Qt.UserRole)
        session = self.session_manager.get_session(session_index)
        
        if session and session.type == 'SSH':
            self.current_session = session
            self.show_loading(f"Connecting to {session.host}...")
            
            # Clear terminal
            self.terminal_output.clear()
            
            # Start SSH connection in thread
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
        if item:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 4px 20px;
                    font-size: 11px;
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
                self.delete_session_item(item)
            elif action == edit_action:
                self.edit_session_item(item)
    
    def delete_session_item(self, item):
        session_index = item.data(Qt.UserRole)
        session = self.session_manager.get_session(session_index)
        
        if session and self.session_manager.confirm_delete_session(self, session.host):
            if self.session_manager.delete_session(session_index):
                self.sessions_list.takeItem(self.sessions_list.row(item))
    
    def edit_session_item(self, item):
        session_index = item.data(Qt.UserRole)
        session = self.session_manager.get_session(session_index)
        
        if session:
            dialog = SessionDialog(self, session)
            if dialog.exec_() == QDialog.Accepted:
                updated_session = dialog.get_session_data()
                if self.session_manager.update_session(session_index, updated_session):
                    item.setText(updated_session.host)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MobaXtermClone()
    window.show()
    sys.exit(app.exec_())