from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QShortcut
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QTextCursor

try:
    import pyte
except Exception:
    pyte = None

class Terminal2(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._send_key = None
        self._stream = None
        self._screen = None
        # Normal/alternate screen support for full-screen apps (vim, less)
        self._normal_screen = None
        self._normal_stream = None
        self._alt_screen = None
        self._alt_stream = None
        self._using_alt = False
        self._normal_snapshot = []
        if pyte is not None:
            self._normal_screen = pyte.Screen(200, 50)
            self._normal_stream = pyte.Stream(self._normal_screen)
            self._screen = self._normal_screen
            self._stream = self._normal_stream
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render)
        self._pending = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QTextEdit()
        self.view.setReadOnly(False)
        self.view.setLineWrapMode(QTextEdit.NoWrap)
        self.view.setStyleSheet("QTextEdit{background:#0f111a;color:#e6e6e6;border:none;padding:6px}")
        font = QFont('Consolas')
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.view.setFont(font)
        layout.addWidget(self.view)
        # input handling
        self.view.installEventFilter(self)
        self.view.viewport().installEventFilter(self)
        # shortcuts
        try:
            sc_in = QShortcut(QKeySequence.ZoomIn, self)
            sc_in.activated.connect(lambda: self.view.zoomIn(1))
            sc_out = QShortcut(QKeySequence.ZoomOut, self)
            sc_out.activated.connect(lambda: self.view.zoomOut(1))
        except Exception:
            pass

    def set_sender(self, sender):
        self._send_key = sender
    def _send(self, data: str):
        if self._send_key and data is not None:
            try:
                self._send_key(data)
            except Exception:
                pass

    def feed(self, data: str):
        if self._stream is None:
            # fallback
            self.view.moveCursor(QTextCursor.End)
            self.view.insertPlainText(data)
            return
        try:
            # Intercept alternate screen enable/disable sequences
            data = self._handle_alt_screen_sequences(data)
            self._stream.feed(data)
            if not self._pending:
                self._pending = True
                self._render_timer.start(33)
        except Exception:
            pass

    # Compatibility with existing SSHThread wiring
    def append_output(self, text: str):
        try:
            self.feed(text)
        except Exception:
            pass

    def _handle_alt_screen_sequences(self, s: str) -> str:
        # Handle DEC Private Modes ?1049, ?47, ?1047
        # Enter alt: ESC [ ? 1049 h (or 47/1047); Exit alt: ESC [ ? 1049 l
        try:
            import re
            def enter_alt():
                if not self._using_alt and pyte is not None:
                    self._using_alt = True
                    # Snapshot current view lines to restore later
                    try:
                        doc = self.view.document()
                        lines = []
                        blk = doc.firstBlock()
                        while blk.isValid():
                            lines.append(blk.text())
                            blk = blk.next()
                        self._normal_snapshot = lines
                    except Exception:
                        self._normal_snapshot = []
                    # Create alt screen/stream fresh
                    self._alt_screen = pyte.Screen(self._normal_screen.columns, self._normal_screen.lines)
                    self._alt_stream = pyte.Stream(self._alt_screen)
                    self._screen = self._alt_screen
                    self._stream = self._alt_stream

            def exit_alt():
                if self._using_alt and pyte is not None:
                    self._using_alt = False
                    # Switch back to normal screen/stream
                    self._screen = self._normal_screen
                    self._stream = self._normal_stream
                    # Restore snapshot to the view immediately
                    try:
                        self.view.setPlainText("\n".join(self._normal_snapshot))
                    except Exception:
                        pass

            # Enter alt matches
            s = re.sub(r"\x1b\[\?(?:1049|47|1047)h", lambda m: enter_alt() or "", s)
            # Exit alt matches
            s = re.sub(r"\x1b\[\?(?:1049|47|1047)l", lambda m: exit_alt() or "", s)
            return s
        except Exception:
            return s

    def _render(self):
        self._pending = False
        try:
            lines = list(self._screen.display)
        except Exception:
            lines = []
        # Keep viewport stable in alt-screen; outside alt-screen trim trailing blanks
        if self._using_alt:
            height = getattr(self._screen, 'lines', len(lines))
            if len(lines) < height:
                lines += [""] * (height - len(lines))
        else:
            while lines and not (lines[-1] or '').strip():
                lines.pop()
        self.view.setPlainText("\n".join(lines))
        # caret
        try:
            doc = self.view.document()
            row = max(0, min(self._screen.cursor.y, doc.blockCount()-1))
            block = doc.findBlockByNumber(row)
            text = block.text() if block.isValid() else ''
            col = max(0, min(self._screen.cursor.x, len(text)))
            c = self.view.textCursor()
            if block.isValid():
                c.setPosition(block.position()+col)
            else:
                c.movePosition(QTextCursor.End)
            self.view.setTextCursor(c)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if obj in (self.view, self.view.viewport()):
            if event.type() == QEvent.KeyPress:
                key = event.key()
                mods = event.modifiers()
                # Paste Ctrl+Shift+V
                if (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier) and key == Qt.Key_V:
                    try:
                        from PyQt5.QtWidgets import QApplication
                        text = QApplication.clipboard().text()
                        if text:
                            self._send(text)
                    except Exception:
                        pass
                    return True
                # Treat Cut (Ctrl+X) as Copy (do not delete text locally)
                if (mods & Qt.ControlModifier) and key == Qt.Key_X:
                    try:
                        from PyQt5.QtWidgets import QApplication
                        c = self.view.textCursor()
                        if c.hasSelection():
                            QApplication.clipboard().setText(c.selectedText())
                            # Do not remove text from terminal view
                    except Exception:
                        pass
                    return True
                # ESC
                if key == Qt.Key_Escape:
                    self._send("\x1b")
                    return True
                # Ctrl combos
                if (mods & Qt.ControlModifier) and key == Qt.Key_C:
                    self._send("\x03"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_D:
                    self._send("\x04"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_L:
                    self._send("\x0c"); return True
                # Enter
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._send("\r"); return True
                # Backspace
                if key == Qt.Key_Backspace:
                    self._send("\x7f"); return True
                # Tab
                if key == Qt.Key_Tab:
                    self._send("\t"); return True
                # Arrows
                if key == Qt.Key_Up:
                    self._send("\x1b[A"); return True
                if key == Qt.Key_Down:
                    self._send("\x1b[B"); return True
                if key == Qt.Key_Right:
                    self._send("\x1b[C"); return True
                if key == Qt.Key_Left:
                    self._send("\x1b[D"); return True
                # Printable
                txt = event.text()
                if txt:
                    self._send(txt)
                    return True
        return super().eventFilter(obj, event)

