from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTextEdit, 
                             QHBoxLayout, QLineEdit, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QTextCursor
import re

class TerminalTab(QWidget):
    command_submitted = pyqtSignal(str)
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._send_key = None  # callable that sends raw data to SSH
        self._send_queue = []  # buffer keys until sender is ready
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
        # Some key events are delivered to the viewport; filter there too
        self.terminal_output.viewport().installEventFilter(self)
        self.terminal_output.setCursorWidth(2)
        self.terminal_output.setFocusPolicy(Qt.StrongFocus)
        try:
            # Keep Tab inside the widget, not as focus-change
            self.terminal_output.setTabChangesFocus(False)
        except Exception:
            pass
        self.terminal_output.setReadOnly(True)
        
        # State for inline input handling
        self.input_enabled = False
        self.current_input = ""
        self.prompt_text = "$ "
        # Local echo is off by default; remote shell echoes characters
        self.local_echo_enabled = False
        
        # Only the terminal area is shown; input happens inline
        layout.addWidget(self.terminal_output)
        
    def enable_input(self):
        self.input_enabled = True
        # Make editable so caret blinks; eventFilter prevents local edits
        self.terminal_output.setReadOnly(False)
        self.terminal_output.setFocus()
        self.current_input = ""
        
    def disable_input(self):
        self.input_enabled = False
        self.terminal_output.setReadOnly(True)
        
    def append_output(self, text):
        # Strip ANSI/OSC sequences for readability in QTextEdit
        cleaned = self._strip_ansi(text)
        # Normalize line endings
        # Convert CRLF and bare CR to LF
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        self._write(cleaned)
        # Auto-scroll to bottom
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.terminal_output.setTextCursor(cursor)

    def _write(self, text: str):
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.terminal_output.setTextCursor(cursor)

    def set_key_sender(self, sender_callable):
        """Provide a callable that will be used to send raw key data to SSH."""
        self._send_key = sender_callable
        # Flush any queued input collected before sender was ready
        if self._send_queue:
            try:
                self._send_key(''.join(self._send_queue))
            finally:
                self._send_queue.clear()

    def _send(self, data: str):
        if self._send_key is not None and data is not None:
            try:
                self._send_key(data)
            except Exception:
                # Silently ignore send errors in UI layer
                pass
        else:
            # Queue input until transport is ready
            if data:
                self._send_queue.append(data)

    def eventFilter(self, obj, event):
        if obj in (self.terminal_output, self.terminal_output.viewport()) and event.type() == QEvent.KeyPress:
            if not self.input_enabled:
                return True if self.terminal_output.isReadOnly() else False
            key = event.key()
            modifiers = event.modifiers()
            # Ctrl+C
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_C:
                self._send("\x03")  # ETX
                return True
            # Ctrl+D
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_D:
                self._send("\x04")  # EOT
                return True
            # Ctrl+S should not freeze: send XOFF only if we really want to; otherwise ignore
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_S:
                # ignore to prevent terminal freeze
                return True
            # Enter / Return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                # Most PTYs expect CR; bash will map CR to NL via icrnl
                self._send("\r")
                return True
            # Backspace
            if key == Qt.Key_Backspace:
                # Send Backspace as DEL; many shells map it correctly
                self._send("\x7f")
                # Also send Ctrl+H as compatibility fallback
                self._send("\x08")
                return True
            # Tab completion
            if key == Qt.Key_Tab:
                self._send("\t")
                return True
            # Arrow keys and navigation as ANSI sequences
            if key == Qt.Key_Up:
                self._send("\x1b[A")
                return True
            if key == Qt.Key_Down:
                self._send("\x1b[B")
                return True
            if key == Qt.Key_Right:
                self._send("\x1b[C")
                return True
            if key == Qt.Key_Left:
                self._send("\x1b[D")
                return True
            if key == Qt.Key_Home:
                self._send("\x1b[H")
                return True
            if key == Qt.Key_End:
                self._send("\x1b[F")
                return True
            if key == Qt.Key_PageUp:
                self._send("\x1b[5~")
                return True
            if key == Qt.Key_PageDown:
                self._send("\x1b[6~")
                return True
            if key == Qt.Key_Delete:
                self._send("\x1b[3~")
                return True
            # Ctrl+L clear screen
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_L:
                self._send("\x0c")
                return True
            # Printable characters
            text = event.text()
            if text:
                if self.local_echo_enabled:
                    self._write(text)
                self._send(text)
                return True
        return super().eventFilter(obj, event)

    def _strip_ansi(self, s: str) -> str:
        """Remove ANSI control sequences (CSI, OSC, etc.) so QTextEdit shows clean text."""
        # OSC sequences: ESC ] ... BEL or ESC \
        osc_pattern = re.compile(r"\x1B\][\x20-\x7E]*?(\x07|\x1B\\)")
        # CSI sequences: ESC [ ... Cmd
        csi_pattern = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        # Single-char ESC sequences
        esc_pattern = re.compile(r"\x1B[@-Z\\-_]")
        s = osc_pattern.sub('', s)
        s = csi_pattern.sub('', s)
        s = esc_pattern.sub('', s)
        return s

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