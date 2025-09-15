from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTextEdit, 
                             QHBoxLayout, QLineEdit, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

class TerminalTab(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                border: none;
                padding: 5px;
            }
        """)
        self.terminal_output.setPlainText("")
        
        # Command input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setSpacing(5)
        input_layout.setContentsMargins(0, 5, 0, 0)
        
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 16px;")
        self.prompt_label.setFixedWidth(20)
        
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("""
            QLineEdit {
                background-color: black;
                color: #00ff00;
                border: 1px solid #555;
                border-radius: 2px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }
        """)
        self.command_input.setDisabled(True)
        self.command_input.setPlaceholderText("Type command...")
        
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.command_input)
        
        layout.addWidget(self.terminal_output)
        layout.addWidget(input_container)
        
    def enable_input(self):
        self.command_input.setDisabled(False)
        self.command_input.setFocus()
        
    def disable_input(self):
        self.command_input.setDisabled(True)
        
    def append_output(self, text):
        self.terminal_output.append(text)
        # Auto-scroll to bottom
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.terminal_output.setTextCursor(cursor)

class TerminalTabs(QTabWidget):
    tab_close_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-top: none;
                background: white;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #ccc;
                border-bottom-color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
            }
            QTabBar::close-button {
                image: url(none);
                subcontrol-position: right;
                padding: 4px;
            }
            QTabBar::close-button:hover {
                background: #ff4757;
                border-radius: 8px;
            }
        """)
        
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.on_tab_close)
        
    def on_tab_close(self, index):
        self.tab_close_requested.emit(index)
        
    def add_terminal_tab(self, session):
        tab = TerminalTab(session)
        tab_index = self.addTab(tab, f"🖥️ {session.host}")
        self.setCurrentIndex(tab_index)
        return tab
        
    def get_current_terminal(self):
        current_widget = self.currentWidget()
        if isinstance(current_widget, TerminalTab):
            return current_widget
        return None