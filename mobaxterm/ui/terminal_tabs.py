from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTextEdit, 
                             QHBoxLayout, QLineEdit, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QTextCursor

class TerminalTab(QWidget):
    command_submitted = pyqtSignal(str)
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Terminal output (now also used for input)
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
        self.terminal_output.installEventFilter(self)
        self.terminal_output.setCursorWidth(2)
        self.terminal_output.setReadOnly(True)
        
        # State for inline input handling
        self.input_enabled = False
        self.current_input = ""
        self.prompt_text = "$ "
        
        # Only the terminal area is shown; input happens inline
        layout.addWidget(self.terminal_output)
        
    def enable_input(self):
        self.input_enabled = True
        self.terminal_output.setReadOnly(False)
        self.terminal_output.setFocus()
        self.current_input = ""
        self._write(self.prompt_text)
        
    def disable_input(self):
        self.input_enabled = False
        self.terminal_output.setReadOnly(True)
        
    def append_output(self, text):
        self.terminal_output.append(text)
        # Auto-scroll to bottom
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.terminal_output.setTextCursor(cursor)

    def _write(self, text: str):
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.terminal_output.setTextCursor(cursor)

    def eventFilter(self, obj, event):
        if obj is self.terminal_output and event.type() == QEvent.KeyPress:
            if not self.input_enabled:
                return True if self.terminal_output.isReadOnly() else False
            key = event.key()
            # Handle Enter
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._write("\n")
                command = self.current_input
                self.current_input = ""
                self.command_submitted.emit(command)
                return True
            # Handle Backspace
            if key == Qt.Key_Backspace:
                if len(self.current_input) > 0:
                    self.current_input = self.current_input[:-1]
                    cursor = self.terminal_output.textCursor()
                    cursor.movePosition(QTextCursor.End)
                    cursor.deletePreviousChar()
                    self.terminal_output.setTextCursor(cursor)
                return True
            # Block navigation/editing keys to keep cursor at end
            if key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_PageUp, Qt.Key_PageDown):
                return True
            # Printable text
            text = event.text()
            if text:
                self.current_input += text
                self._write(text)
                return True
        return super().eventFilter(obj, event)

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