from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QCheckBox, QSpinBox, QGroupBox,

                             QDialogButtonBox, QGridLayout, QStackedWidget, QWidget, QComboBox,
                             QFileDialog, QInputDialog, QSizePolicy)
from PyQt5.QtCore import Qt
from ..models.session import Session

class SessionDialog(QDialog):
    def __init__(self, parent=None, session: Session = None):
        super().__init__(parent)
        self.setWindowTitle("Session settings")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.current_tab = "SSH"
        self.editing_session = session is not None
        self.session_to_edit = session
        self.parent = parent
        self.initUI()
        
        if session:
            self.load_session_data(session)
        
    def initUI(self):
        # Основные стили
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                font-size: 12px;
            }
            QLabel {
                font-size: 12px;
                color: #333;
            }
            QLineEdit, QSpinBox, QComboBox {
                font-size: 12px;
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                min-height: 28px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #0078d7;
            }
            QPushButton {
                font-size: 12px;
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #ccc;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:checked {
                background-color: #0078d7;
                color: white;
                border-color: #005fa3;
            }
            QCheckBox {
                font-size: 12px;
                spacing: 5px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #0078d7;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
                min-height: 30px;
            }
            QDialogButtonBox QPushButton[text="OK"] {
                background-color: #0078d7;
                color: white;
                border-color: #005fa3;
            }
            QDialogButtonBox QPushButton[text="OK"]:hover {
                background-color: #005fa3;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: #6c757d;
                color: white;
                border-color: #545b62;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background-color: #545b62;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # SSH/SFTP tabs
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(5)
        
        self.ssh_btn = QPushButton("SSH")
        self.sftp_btn = QPushButton("SFTP")
        
        for btn in [self.ssh_btn, self.sftp_btn]:
            btn.setCheckable(True)
            btn.setFixedHeight(35)
            btn.setFixedWidth(80)
            tabs_layout.addWidget(btn)
        
        self.ssh_btn.setChecked(True)
        
        tabs_layout.addStretch()
        main_layout.addLayout(tabs_layout)
        
        # Stacked widget для разных настроек
        self.stacked_widget = QStackedWidget()
        
        # SSH settings page
        self.ssh_page = QWidget()
        self.init_ssh_page()
        self.stacked_widget.addWidget(self.ssh_page)
        
        # SFTP settings page
        self.sftp_page = QWidget()
        self.init_sftp_page()
        self.stacked_widget.addWidget(self.sftp_page)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Session type label
        self.session_label = QLabel("Secure Shell (SSH) session")
        self.session_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #0078d7;
                font-size: 13px;
                padding: 8px;
                background-color: #f0f8ff;
                border-radius: 4px;
                border: 1px solid #cce5ff;
            }
        """)
        self.session_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.session_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Connect signals
        self.ssh_btn.clicked.connect(self.switch_to_ssh)
        self.sftp_btn.clicked.connect(self.switch_to_sftp)
        
    def get_tab_style(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: 1px solid #005fa3;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f8f9fa;
                    color: #495057;
                    border: 1px solid #dee2e6;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """
    
    def init_ssh_page(self):
        layout = QVBoxLayout(self.ssh_page)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Basic SSH settings group
        basic_group = QGroupBox("Basic SSH settings")
        basic_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(12, 15, 12, 12)
        basic_layout.setColumnStretch(0, 0)
        basic_layout.setColumnStretch(1, 1)
        
        # Row 0: Remote host
        host_label = QLabel("Remote host:")
        host_label.setMinimumWidth(100)
        basic_layout.addWidget(host_label, 0, 0, Qt.AlignRight)
        
        self.ssh_host_input = QLineEdit()
        self.ssh_host_input.setPlaceholderText("hostname or IP")
        self.ssh_host_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_host_input, 0, 1)
        
        # Row 1: Username checkbox
        self.ssh_username_check = QCheckBox("Specify username")
        basic_layout.addWidget(self.ssh_username_check, 1, 1)
        
        # Row 2: Username label and input
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        basic_layout.addWidget(username_label, 2, 0, Qt.AlignRight)
        
        self.ssh_username_input = QLineEdit()
        self.ssh_username_input.setPlaceholderText("username")
        self.ssh_username_input.setEnabled(False)
        self.ssh_username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_username_input, 2, 1)
        
        # Row 3: Password label and input
        password_label = QLabel("Password:")
        password_label.setMinimumWidth(100)
        basic_layout.addWidget(password_label, 3, 0, Qt.AlignRight)
        
        self.ssh_password_input = QLineEdit()
        self.ssh_password_input.setEchoMode(QLineEdit.Password)
        self.ssh_password_input.setPlaceholderText("password")
        self.ssh_password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_password_input, 3, 1)
        
        # Row 4: Port checkbox
        self.ssh_port_check = QCheckBox("Custom port")
        basic_layout.addWidget(self.ssh_port_check, 4, 1)
        
        # Row 5: Port label and input
        port_label = QLabel("Port:")
        port_label.setMinimumWidth(100)
        basic_layout.addWidget(port_label, 5, 0, Qt.AlignRight)
        
        self.ssh_port_input = QSpinBox()
        self.ssh_port_input.setRange(1, 65535)
        self.ssh_port_input.setValue(22)
        self.ssh_port_input.setEnabled(False)
        self.ssh_port_input.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_port_input, 5, 1)
        
        # Row 6: Folder label and combo
        folder_label = QLabel("Folder:")
        folder_label.setMinimumWidth(100)
        basic_layout.addWidget(folder_label, 6, 0, Qt.AlignRight)
        
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("(No folder)", None)
        
        # Load existing folders
        if self.parent and hasattr(self.parent, 'session_manager'):
            folders = self.parent.session_manager.get_all_folders()
            for folder in folders:
                self.folder_combo.addItem(folder, folder)
        
        self.folder_combo.addItem("+ Create new folder...", "new")
        basic_layout.addWidget(self.folder_combo, 6, 1)
        
        layout.addWidget(basic_group)
        
        # Authentication group
        auth_group = QGroupBox("Authentication")
        auth_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        auth_layout = QGridLayout(auth_group)
        auth_layout.setSpacing(8)
        auth_layout.setContentsMargins(12, 15, 12, 12)
        auth_layout.setColumnStretch(0, 0)
        auth_layout.setColumnStretch(1, 1)

        # Row 0: Method
        auth_method_label = QLabel("Method:")
        auth_method_label.setMinimumWidth(100)
        auth_layout.addWidget(auth_method_label, 0, 0, Qt.AlignRight)

        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItem("Password", "password")
        self.auth_method_combo.addItem("SSH key", "key")
        auth_layout.addWidget(self.auth_method_combo, 0, 1)

        # Row 1: Private key path
        key_path_label = QLabel("Private key:")
        key_path_label.setMinimumWidth(100)
        auth_layout.addWidget(key_path_label, 1, 0, Qt.AlignRight)

        key_path_container = QWidget()
        key_path_h = QHBoxLayout(key_path_container)
        key_path_h.setContentsMargins(0, 0, 0, 0)
        key_path_h.setSpacing(6)
        self.key_path_input = QLineEdit()
        self.key_path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.key_path_browse = QPushButton("Browse…")
        self.key_path_browse.setFixedWidth(90)
        key_path_h.addWidget(self.key_path_input)
        key_path_h.addWidget(self.key_path_browse)
        auth_layout.addWidget(key_path_container, 1, 1)

        # Row 2: Passphrase
        passphrase_label = QLabel("Passphrase:")
        passphrase_label.setMinimumWidth(100)
        auth_layout.addWidget(passphrase_label, 2, 0, Qt.AlignRight)

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.passphrase_input, 2, 1)

        layout.addWidget(auth_group)

        # Advanced SSH settings group
        advanced_group = QGroupBox("Advanced SSH settings")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(8)
        advanced_layout.setContentsMargins(12, 15, 12, 12)
        
        self.ssh_terminal_check = QCheckBox("Terminal settings")
        self.ssh_network_check = QCheckBox("Network settings")
        self.ssh_bookmark_check = QCheckBox("Bookmark settings")
        
        advanced_layout.addWidget(self.ssh_terminal_check)
        advanced_layout.addWidget(self.ssh_network_check)
        advanced_layout.addWidget(self.ssh_bookmark_check)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        # Connect signals
        self.ssh_username_check.toggled.connect(self.toggle_username_field)
        self.ssh_port_check.toggled.connect(self.toggle_port_field)
        self.folder_combo.currentIndexChanged.connect(self.on_folder_changed)
        self.auth_method_combo.currentIndexChanged.connect(self.on_auth_method_changed)
        self.key_path_browse.clicked.connect(self.on_browse_key)

        # Initialize auth controls state
        self.on_auth_method_changed(self.auth_method_combo.currentIndex())
        
    def on_folder_changed(self, index):
        if self.folder_combo.currentData() == "new":
            folder_name, ok = QInputDialog.getText(
                self, 
                "New Folder", 
                "Enter folder name:",
                QLineEdit.Normal
            )
            
            if ok and folder_name:
                if self.parent and hasattr(self.parent, 'session_manager'):
                    if self.parent.session_manager.add_folder(folder_name):
                        self.folder_combo.insertItem(self.folder_combo.count() - 1, folder_name, folder_name)
                        self.folder_combo.setCurrentText(folder_name)
                else:
                    self.folder_combo.setCurrentIndex(0)
        
    def toggle_username_field(self, checked):
        self.ssh_username_input.setEnabled(checked)
        if not checked:
            self.ssh_username_input.clear()
    
    def toggle_port_field(self, checked):
        self.ssh_port_input.setEnabled(checked)
        if not checked:
            self.ssh_port_input.setValue(22)
    
    def init_sftp_page(self):
        layout = QVBoxLayout(self.sftp_page)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        basic_group = QGroupBox("Basic SFTP settings")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(12, 15, 12, 12)
        basic_layout.setColumnStretch(0, 0)
        basic_layout.setColumnStretch(1, 1)
        
        # Row 0: Remote host
        host_label = QLabel("Remote host:")
        host_label.setMinimumWidth(100)
        basic_layout.addWidget(host_label, 0, 0, Qt.AlignRight)
        
        self.sftp_host_input = QLineEdit()
        self.sftp_host_input.setPlaceholderText("hostname or IP")
        self.sftp_host_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.sftp_host_input, 0, 1)
        
        # Row 1: Username
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        basic_layout.addWidget(username_label, 1, 0, Qt.AlignRight)
        
        self.sftp_username_input = QLineEdit()
        self.sftp_username_input.setPlaceholderText("username")
        self.sftp_username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.sftp_username_input, 1, 1)
        
        # Row 2: Password
        password_label = QLabel("Password:")
        password_label.setMinimumWidth(100)
        basic_layout.addWidget(password_label, 2, 0, Qt.AlignRight)
        
        self.sftp_password_input = QLineEdit()
        self.sftp_password_input.setEchoMode(QLineEdit.Password)
        self.sftp_password_input.setPlaceholderText("password")
        self.sftp_password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.sftp_password_input, 2, 1)
        
        # Row 3: Port
        port_label = QLabel("Port:")
        port_label.setMinimumWidth(100)
        basic_layout.addWidget(port_label, 3, 0, Qt.AlignRight)
        
        self.sftp_port_input = QSpinBox()
        self.sftp_port_input.setRange(1, 65535)
        self.sftp_port_input.setValue(22)
        self.sftp_port_input.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        basic_layout.addWidget(self.sftp_port_input, 3, 1)
        
        # Row 4: Folder
        folder_label = QLabel("Folder:")
        folder_label.setMinimumWidth(100)
        basic_layout.addWidget(folder_label, 4, 0, Qt.AlignRight)
        
        self.sftp_folder_combo = QComboBox()
        self.sftp_folder_combo.addItem("(No folder)", None)
        
        if self.parent and hasattr(self.parent, 'session_manager'):
            folders = self.parent.session_manager.get_all_folders()
            for folder in folders:
                self.sftp_folder_combo.addItem(folder, folder)
        
        self.sftp_folder_combo.addItem("+ Create new folder...", "new")
        basic_layout.addWidget(self.sftp_folder_combo, 4, 1)
        
        layout.addWidget(basic_group)
        
        advanced_group = QGroupBox("Advanced SFTP settings")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(8)
        advanced_layout.setContentsMargins(12, 15, 12, 12)
        
        self.sftp_bookmark_check = QCheckBox("Bookmark settings")
        advanced_layout.addWidget(self.sftp_bookmark_check)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        self.sftp_folder_combo.currentIndexChanged.connect(self.on_sftp_folder_changed)
        
    def on_sftp_folder_changed(self, index):
        if self.sftp_folder_combo.currentData() == "new":
            folder_name, ok = QInputDialog.getText(
                self, 
                "New Folder", 
                "Enter folder name:",
                QLineEdit.Normal
            )
            
            if ok and folder_name:
                if self.parent and hasattr(self.parent, 'session_manager'):
                    if self.parent.session_manager.add_folder(folder_name):
                        self.sftp_folder_combo.insertItem(self.sftp_folder_combo.count() - 1, folder_name, folder_name)
                        self.sftp_folder_combo.setCurrentText(folder_name)
                else:
                    self.sftp_folder_combo.setCurrentIndex(0)
        
    def switch_to_ssh(self):
        self.current_tab = "SSH"
        self.ssh_btn.setChecked(True)
        self.sftp_btn.setChecked(False)
        
        self.ssh_btn.setStyleSheet(self.get_tab_style(True))
        self.sftp_btn.setStyleSheet(self.get_tab_style(False))
        
        self.stacked_widget.setCurrentIndex(0)
        self.session_label.setText("Secure Shell (SSH) session")
        
    def switch_to_sftp(self):
        self.current_tab = "SFTP"
        self.sftp_btn.setChecked(True)
        self.ssh_btn.setChecked(False)
        
        self.sftp_btn.setStyleSheet(self.get_tab_style(True))
        self.ssh_btn.setStyleSheet(self.get_tab_style(False))
        
        self.stacked_widget.setCurrentIndex(1)
        self.session_label.setText("SFTP session")
        
    def load_session_data(self, session: Session):
        if session.type == 'SSH':
            self.ssh_btn.click()
            self.ssh_host_input.setText(session.host)
            
            if session.username:
                self.ssh_username_check.setChecked(True)
                self.ssh_username_input.setText(session.username)
                self.ssh_username_input.setEnabled(True)
            
            if session.password:
                self.ssh_password_input.setText(session.password)
            
            if session.port != 22:
                self.ssh_port_check.setChecked(True)
                self.ssh_port_input.setValue(session.port)
                self.ssh_port_input.setEnabled(True)
            
            if session.folder:
                index = self.folder_combo.findData(session.folder)
                if index >= 0:
                    self.folder_combo.setCurrentIndex(index)
            
            self.ssh_terminal_check.setChecked(session.terminal_settings)
            self.ssh_network_check.setChecked(session.network_settings)
            self.ssh_bookmark_check.setChecked(session.bookmark_settings)
            # Load auth
            if hasattr(session, 'auth_method'):
                method_index = self.auth_method_combo.findData(session.auth_method)
                if method_index >= 0:
                    self.auth_method_combo.setCurrentIndex(method_index)
            if hasattr(session, 'private_key_path') and session.private_key_path:
                self.key_path_input.setText(session.private_key_path)
            if hasattr(session, 'private_key_passphrase') and session.private_key_passphrase:
                self.passphrase_input.setText(session.private_key_passphrase)
            
        else:
            self.sftp_btn.click()
            self.sftp_host_input.setText(session.host)
            self.sftp_username_input.setText(session.username or "")
            self.sftp_port_input.setValue(session.port)
            if session.password:
                self.sftp_password_input.setText(session.password)
            
            if session.folder:
                index = self.sftp_folder_combo.findData(session.folder)
                if index >= 0:
                    self.sftp_folder_combo.setCurrentIndex(index)
            
            self.sftp_bookmark_check.setChecked(session.bookmark_settings)
        
    def get_session_data(self) -> Session:
        if self.current_tab == "SSH":
            session = Session(
                type='SSH',
                host=self.ssh_host_input.text(),
                port=self.ssh_port_input.value() if self.ssh_port_check.isChecked() else 22,
                username=self.ssh_username_input.text() if self.ssh_username_check.isChecked() else None,
                auth_method=self.auth_method_combo.currentData(),
                private_key_path=self.key_path_input.text() if self.auth_method_combo.currentData() == 'key' and self.key_path_input.text() else None,
                private_key_passphrase=self.passphrase_input.text() if self.auth_method_combo.currentData() == 'key' and self.passphrase_input.text() else None,
                terminal_settings=self.ssh_terminal_check.isChecked(),
                network_settings=self.ssh_network_check.isChecked(),
                bookmark_settings=self.ssh_bookmark_check.isChecked()
            )
            session.folder = self.folder_combo.currentData()
            return session
        else:
            session = Session(
                type='SFTP',
                host=self.sftp_host_input.text(),
                port=self.sftp_port_input.value(),
                username=self.sftp_username_input.text(),
                password=self.sftp_password_input.text() if hasattr(self, 'sftp_password_input') else None,
                bookmark_settings=self.sftp_bookmark_check.isChecked()
            )
            session.folder = self.sftp_folder_combo.currentData()
            return session

    def on_auth_method_changed(self, index):
        method = self.auth_method_combo.currentData()
        is_key = method == 'key'
        self.key_path_input.setEnabled(is_key)
        self.key_path_browse.setEnabled(is_key)
        self.passphrase_input.setEnabled(is_key)

    def on_browse_key(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "All Files (*)")
        if file_path:
            self.key_path_input.setText(file_path)