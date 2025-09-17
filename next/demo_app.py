from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel
from PyQt5.QtCore import Qt
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
        self.term = TerminalWeb()
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
        self.term.set_sender(lambda data: self.ssh.send(data))

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Demo()
    w.show()
    sys.exit(app.exec_())

