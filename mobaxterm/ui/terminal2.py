from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QShortcut
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
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
        if pyte is not None:
            self._screen = pyte.Screen(200, 50)
            self._stream = pyte.Stream(self._screen)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render)
        self._pending = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QTextEdit.NoWrap)
        self.view.setStyleSheet("QTextEdit{background:#0f111a;color:#e6e6e6;border:none;padding:6px}")
        font = QFont('Consolas')
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.view.setFont(font)
        layout.addWidget(self.view)
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

    def feed(self, data: str):
        if self._stream is None:
            # fallback
            self.view.moveCursor(QTextCursor.End)
            self.view.insertPlainText(data)
            return
        try:
            self._stream.feed(data)
            if not self._pending:
                self._pending = True
                self._render_timer.start(33)
        except Exception:
            pass

    def _render(self):
        self._pending = False
        try:
            lines = list(self._screen.display)
        except Exception:
            lines = []
        height = getattr(self._screen, 'lines', len(lines))
        if len(lines) < height:
            lines += [""] * (height - len(lines))
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

