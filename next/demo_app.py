from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QTextEdit, QShortcut
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QTextCursor
import sys
from terminal_web import TerminalWeb
from ssh_backend import SSHBackend
from sftp_backend import SFTPBackend

class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('WebTerm SSH/SFTP Demo')
        self.resize(1200, 700)
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.ed_host = QLineEdit('localhost')
        self.ed_port = QLineEdit('22')
        self.ed_user = QLineEdit('root')
        self.ed_pass = QLineEdit('')
        self.ed_pass.setEchoMode(QLineEdit.Password)
        btn_connect = QPushButton('Connect SSH')
        btn_connect.clicked.connect(self.on_connect)
        left.addWidget(QLabel('Host'))
        left.addWidget(self.ed_host)
        left.addWidget(QLabel('Port'))
        left.addWidget(self.ed_port)
        left.addWidget(QLabel('User'))
        left.addWidget(self.ed_user)
        left.addWidget(QLabel('Password'))
        left.addWidget(self.ed_pass)
        left.addWidget(btn_connect)
        left.addStretch()

        right = QVBoxLayout()
        # Try WebEngine terminal; fallback to simple QTextEdit terminal
        try:
            self.term = TerminalWeb()
            self._term_is_web = True
        except Exception:
            self.term = TerminalStub()
            self._term_is_web = False
        right.addWidget(self.term)

        bottom = QHBoxLayout()
        self.sftp_list = QListWidget()
        btn_ls = QPushButton('SFTP List /root')
        btn_ls.clicked.connect(self.on_ls)
        bottom.addWidget(self.sftp_list)
        bottom.addWidget(btn_ls)
        right.addLayout(bottom)

        layout.addLayout(left, 1)
        layout.addLayout(right, 3)

        self.ssh = SSHBackend()
        self.ssh.output.connect(self.term.append_output)
        self.ssh.status.connect(lambda ok,msg: print('SSH:',msg))
        # wire key sender
        try:
            self.term.set_sender(lambda data: self.ssh.send(data))
        except Exception:
            pass

        self.sftp = SFTPBackend()
        self.sftp.status.connect(lambda ok,msg: print('SFTP:',msg))
        self.sftp.listing.connect(self.on_listing)

    def on_connect(self):
        host = self.ed_host.text().strip()
        port = int(self.ed_port.text().strip() or '22')
        user = self.ed_user.text().strip()
        pwd = self.ed_pass.text()
        self.ssh.connect(host, port, user, password=pwd, auth_method='password')
        self.sftp.connect(host, port, user, password=pwd, auth_method='password')

    def on_ls(self):
        self.sftp.listdir('/root')

    def on_listing(self, path, entries):
        self.sftp_list.clear()
        for e in entries:
            self.sftp_list.addItem(f"{e['filename']}  {e['st_size']}")

class TerminalStub(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._send = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        self.view = QTextEdit()
        self.view.setReadOnly(False)
        self.view.setLineWrapMode(QTextEdit.NoWrap)
        f = QFont('Consolas'); f.setStyleHint(QFont.Monospace); f.setFixedPitch(True); f.setPointSize(12)
        self.view.setFont(f)
        self.view.installEventFilter(self)
        self.view.viewport().installEventFilter(self)
        lay.addWidget(self.view)
        try:
            QShortcut(QKeySequence.ZoomIn, self, activated=lambda: self.view.zoomIn(1))
            QShortcut(QKeySequence.ZoomOut, self, activated=lambda: self.view.zoomOut(1))
        except Exception:
            pass

    def set_sender(self, sender_callable):
        self._send = sender_callable

    def append_output(self, text: str):
        self.view.moveCursor(QTextCursor.End)
        self.view.insertPlainText(text)

    def eventFilter(self, obj, event):
        if obj in (self.view, self.view.viewport()):
            if event.type() == QEvent.KeyPress:
                key = event.key(); mods = event.modifiers()
                # Enter
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    if self._send: self._send("\r"); return True
                # ESC
                if key == Qt.Key_Escape:
                    if self._send: self._send("\x1b"); return True
                # Backspace
                if key == Qt.Key_Backspace:
                    if self._send: self._send("\x7f"); return True
                # Arrows
                if key == Qt.Key_Up:
                    if self._send: self._send("\x1b[A"); return True
                if key == Qt.Key_Down:
                    if self._send: self._send("\x1b[B"); return True
                if key == Qt.Key_Right:
                    if self._send: self._send("\x1b[C"); return True
                if key == Qt.Key_Left:
                    if self._send: self._send("\x1b[D"); return True
                # Ctrl+C / Ctrl+D
                if (mods & Qt.ControlModifier) and key == Qt.Key_C:
                    if self._send: self._send("\x03"); return True
                if (mods & Qt.ControlModifier) and key == Qt.Key_D:
                    if self._send: self._send("\x04"); return True
                # Printable
                txt = event.text()
                if txt and self._send:
                    self._send(txt); return True
        return super().eventFilter(obj, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Demo()
    w.show()
    sys.exit(app.exec_())

