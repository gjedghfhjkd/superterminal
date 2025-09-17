from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QShortcut
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QTextCursor, QFontMetrics

try:
    import pyte
except Exception:
    pyte = None

class MobaTerminal(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._send_key = None
        self._on_resize = None
        # pyte state
        self._normal_screen = None
        self._normal_stream = None
        self._alt_screen = None
        self._alt_stream = None
        self._screen = None
        self._stream = None
        self._using_alt = False
        self._normal_snapshot = []
        if pyte is not None:
            self._normal_screen = pyte.Screen(200, 50)
            self._normal_stream = pyte.Stream(self._normal_screen)
            self._screen = self._normal_screen
            self._stream = self._normal_stream

        # render throttle
        self._pending = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render)

        # resize throttle
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._emit_resize)

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
        self.view.installEventFilter(self)
        self.view.viewport().installEventFilter(self)
        try:
            sc_in = QShortcut(QKeySequence.ZoomIn, self)
            sc_in.activated.connect(lambda: self.view.zoomIn(1))
            sc_out = QShortcut(QKeySequence.ZoomOut, self)
            sc_out.activated.connect(lambda: self.view.zoomOut(1))
        except Exception:
            pass

    def set_sender(self, sender):
        self._send_key = sender

    def set_resizer(self, resizer):
        self._on_resize = resizer
        # Fire once on attach
        self._resize_timer.start(50)

    def _send(self, data: str):
        if self._send_key and data is not None:
            try:
                self._send_key(data)
            except Exception:
                pass

    def feed(self, data: str):
        if self._stream is None:
            self.view.moveCursor(QTextCursor.End)
            self.view.insertPlainText(data)
            return
        try:
            data = self._handle_alt_screen_sequences(data)
            self._stream.feed(data)
            if not self._pending:
                self._pending = True
                self._render_timer.start(33)
        except Exception:
            pass

    def append_output(self, text: str):
        try:
            self.feed(text)
        except Exception:
            pass

    def _handle_alt_screen_sequences(self, s: str) -> str:
        try:
            import re
            def enter_alt():
                if not self._using_alt and pyte is not None:
                    self._using_alt = True
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
                    self._alt_screen = pyte.Screen(self._normal_screen.columns, self._normal_screen.lines)
                    self._alt_stream = pyte.Stream(self._alt_screen)
                    self._screen = self._alt_screen
                    self._stream = self._alt_stream

            def exit_alt():
                if self._using_alt and pyte is not None:
                    self._using_alt = False
                    self._screen = self._normal_screen
                    self._stream = self._normal_stream
                    try:
                        # Trim trailing blanks from snapshot
                        snap = list(self._normal_snapshot)
                        while snap and not (snap[-1] or '').strip():
                            snap.pop()
                        self.view.setPlainText("\n".join(snap))
                    except Exception:
                        pass

            s = re.sub(r"\x1b\[\?(?:1049|47|1047)h", lambda m: enter_alt() or "", s)
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
        if self._using_alt:
            height = getattr(self._screen, 'lines', len(lines))
            if len(lines) < height:
                lines += [""] * (height - len(lines))
        else:
            while lines and not (lines[-1] or '').strip():
                lines.pop()
        self.view.setPlainText("\n".join(lines))
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
                key = event.key(); mods = event.modifiers()
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
                # Treat Cut as Copy
                if (mods & Qt.ControlModifier) and key == Qt.Key_X:
                    try:
                        from PyQt5.QtWidgets import QApplication
                        c = self.view.textCursor()
                        if c.hasSelection():
                            QApplication.clipboard().setText(c.selectedText())
                    except Exception:
                        pass
                    return True
                if key == Qt.Key_Escape:
                    self._send("\x1b"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_C:
                    self._send("\x03"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_D:
                    self._send("\x04"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_L:
                    self._send("\x0c"); return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._send("\r"); return True
                if key == Qt.Key_Backspace:
                    self._send("\x7f"); return True
                if key == Qt.Key_Tab:
                    self._send("\t"); return True
                if key == Qt.Key_Up:
                    self._send("\x1b[A"); return True
                if key == Qt.Key_Down:
                    self._send("\x1b[B"); return True
                if key == Qt.Key_Right:
                    self._send("\x1b[C"); return True
                if key == Qt.Key_Left:
                    self._send("\x1b[D"); return True
                txt = event.text()
                if txt:
                    self._send(txt); return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, e):
        try:
            self._resize_timer.start(50)
        except Exception:
            pass
        return super().resizeEvent(e)

    def _emit_resize(self):
        if not self._on_resize:
            return
        try:
            vp = self.view.viewport()
            w = max(1, vp.width()); h = max(1, vp.height())
            fm = QFontMetrics(self.view.font())
            cw = max(1, fm.horizontalAdvance('M'))
            ch = max(1, fm.lineSpacing())
            cols = max(20, int(w / cw))
            rows = max(5, int(h / ch))
            self._on_resize(cols, rows)
        except Exception:
            pass

