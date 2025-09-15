from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QCheckBox, QSpinBox, QGroupBox,
                             QDialogButtonBox, QGridLayout, QStackedWidget, QWidget)
from PyQt5.QtCore import Qt
from ..models.session import Session

class SessionDialog(QDialog):
    def __init__(self, parent=None, session: Session = None):
        super().__init__(parent)
        self.setWindowTitle("Session settings")
        self.setModal(True)
        self.setFixedSize(500, 450)
        self.current_tab = "SSH"
        self.editing_session = session is not None
        self.session_to_edit = session
        self.initUI()
        
        if session:
            self.load_session_data(session)
        
    def initUI(self):
        # Set white background for the whole dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # SSH/SFTP tabs
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(0)
        
        self.ssh_btn = QPushButton("SSH")
        self.sftp_btn = QPushButton("SFTP")
        
        # Configure tab buttons
        for btn in [self.ssh_btn, self.sftp_btn]:
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setFixedWidth(80)
            btn.setStyleSheet(self.get_tab_style(False))
            tabs_layout.addWidget(btn)
        
        self.ssh_btn.setChecked(True)
        self.ssh_btn.setStyleSheet(self.get_tab_style(True))
        
        tabs_layout.addStretch()
        layout.addLayout(tabs_layout)
        
        # Stacked widget for different settings
        self.stacked_widget = QStackedWidget()
        
        # SSH settings page
        self.ssh_page = QWidget()
        self.init_ssh_page()
        self.stacked_widget.addWidget(self.ssh_page)
        
        # SFTP settings page
        self.sftp_page = QWidget()
        self.init_sftp_page()
        self.stacked_widget.addWidget(self.sftp_page)
        
        layout.addWidget(self.stacked_widget)
        
        # Session type label
        self.session_label = QLabel("Secure Shell (SSH) session")
        self.session_label.setStyleSheet("font-weight: bold; color: #0078d7;")
        layout.addWidget(self.session_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
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
                    padding: 5px;
                    font-weight: bold;
                    border-radius: 3px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #ccc;
                    padding: 5px;
                    font-weight: bold;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """
    
    def init_ssh_page(self):
        layout = QVBoxLayout(self.ssh_page)
        
        # Basic SSH settings group - WHITE COLOR
        basic_group = QGroupBox("📌 Basic SSH settings")
        basic_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: black;
            }
        """)
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("Remote host *"), 0, 0)
        self.ssh_host_input = QLineEdit()
        self.ssh_host_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        basic_layout.addWidget(self.ssh_host_input, 0, 1)
        
        self.ssh_username_check = QCheckBox("Specify username")
        self.ssh_username_check.setStyleSheet("color: black;")
        basic_layout.addWidget(self.ssh_username_check, 1, 0, 1, 2)
        
        # Username input (always visible but disabled by default)
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: black;")
        basic_layout.addWidget(username_label, 2, 0)
        
        self.ssh_username_input = QLineEdit()
        self.ssh_username_input.setPlaceholderText("Enter username")
        self.ssh_username_input.setStyleSheet("background-color: #f5f5f5; color: #999; border: 1px solid #ccc;")
        self.ssh_username_input.setEnabled(False)
        basic_layout.addWidget(self.ssh_username_input, 2, 1)
        
        self.ssh_port_check = QCheckBox("Custom port")
        self.ssh_port_check.setChecked(False)
        self.ssh_port_check.setStyleSheet("color: black;")
        basic_layout.addWidget(self.ssh_port_check, 3, 0)
        
        self.ssh_port_input = QSpinBox()
        self.ssh_port_input.setRange(1, 65535)
        self.ssh_port_input.setValue(22)
        self.ssh_port_input.setStyleSheet("background-color: #f5f5f5; color: #999; border: 1px solid #ccc;")
        self.ssh_port_input.setEnabled(False)
        basic_layout.addWidget(self.ssh_port_input, 3, 1)
        
        layout.addWidget(basic_group)
        
        # Advanced SSH settings group - WHITE COLOR
        advanced_group = QGroupBox("📌 Advanced SSH settings")
        advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: black;
            }
        """)
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.ssh_terminal_check = QCheckBox("Terminal settings")
        self.ssh_terminal_check.setStyleSheet("color: black;")
        self.ssh_network_check = QCheckBox("Network settings")
        self.ssh_network_check.setStyleSheet("color: black;")
        self.ssh_bookmark_check = QCheckBox("Bookmark settings")
        self.ssh_bookmark_check.setStyleSheet("color: black;")
        
        advanced_layout.addWidget(self.ssh_terminal_check)
        advanced_layout.addWidget(self.ssh_network_check)
        advanced_layout.addWidget(self.ssh_bookmark_check)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        # Connect signals
        self.ssh_username_check.toggled.connect(self.toggle_username_field)
        self.ssh_port_check.toggled.connect(self.toggle_port_field)
        
    def toggle_username_field(self, checked):
        self.ssh_username_input.setEnabled(checked)
        if checked:
            self.ssh_username_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        else:
            self.ssh_username_input.setStyleSheet("background-color: #f5f5f5; color: #999; border: 1px solid #ccc;")
            self.ssh_username_input.clear()
    
    def toggle_port_field(self, checked):
        self.ssh_port_input.setEnabled(checked)
        if checked:
            self.ssh_port_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        else:
            self.ssh_port_input.setStyleSheet("background-color: #f5f5f5; color: #999; border: 1px solid #ccc;")
            self.ssh_port_input.setValue(22)
    
    def init_sftp_page(self):
        layout = QVBoxLayout(self.sftp_page)
        
        # Basic SFTP settings group - WHITE COLOR
        basic_group = QGroupBox("📌 Basic SFTP settings")
        basic_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: black;
            }
        """)
        basic_layout = QGridLayout(basic_group)
        
        host_label = QLabel("Remote host ▼")
        host_label.setStyleSheet("color: black;")
        basic_layout.addWidget(host_label, 0, 0)
        self.sftp_host_input = QLineEdit()
        self.sftp_host_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        basic_layout.addWidget(self.sftp_host_input, 0, 1)
        
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: black;")
        basic_layout.addWidget(username_label, 1, 0)
        self.sftp_username_input = QLineEdit()
        self.sftp_username_input.setPlaceholderText("Enter username")
        self.sftp_username_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        basic_layout.addWidget(self.sftp_username_input, 1, 1)
        
        port_label = QLabel("Port")
        port_label.setStyleSheet("color: black;")
        basic_layout.addWidget(port_label, 2, 0)
        self.sftp_port_input = QSpinBox()
        self.sftp_port_input.setRange(1, 65535)
        self.sftp_port_input.setValue(22)
        self.sftp_port_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        basic_layout.addWidget(self.sftp_port_input, 2, 1)
        
        layout.addWidget(basic_group)
        
        # Advanced SFTP settings group - WHITE COLOR
        advanced_group = QGroupBox("📌 Advanced SFTP settings")
        advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: black;
            }
        """)
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.sftp_bookmark_check = QCheckBox("Bookmark settings")
        self.sftp_bookmark_check.setStyleSheet("color: black;")
        advanced_layout.addWidget(self.sftp_bookmark_check)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
    def switch_to_ssh(self):
        self.current_tab = "SSH"
        self.ssh_btn.setChecked(True)
        self.sftp_btn.setChecked(False)
        
        # Update button styles
        self.ssh_btn.setStyleSheet(self.get_tab_style(True))
        self.sftp_btn.setStyleSheet(self.get_tab_style(False))
        
        self.stacked_widget.setCurrentIndex(0)
        self.session_label.setText("Secure Shell (SSH) session")
        
    def switch_to_sftp(self):
        self.current_tab = "SFTP"
        self.sftp_btn.setChecked(True)
        self.ssh_btn.setChecked(False)
        
        # Update button styles
        self.sftp_btn.setStyleSheet(self.get_tab_style(True))
        self.ssh_btn.setStyleSheet(self.get_tab_style(False))
        
        self.stacked_widget.setCurrentIndex(1)
        self.session_label.setText("SFTP session")
        
    def load_session_data(self, session: Session):
        """Load session data into the form for editing"""
        if session.type == 'SSH':
            self.ssh_btn.click()
            self.ssh_host_input.setText(session.host)
            
            if session.username:
                self.ssh_username_check.setChecked(True)
                self.ssh_username_input.setText(session.username)
                self.ssh_username_input.setEnabled(True)
                self.ssh_username_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
            
            if session.port != 22:
                self.ssh_port_check.setChecked(True)
                self.ssh_port_input.setValue(session.port)
                self.ssh_port_input.setEnabled(True)
                self.ssh_port_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
            
            self.ssh_terminal_check.setChecked(session.terminal_settings)
            self.ssh_network_check.setChecked(session.network_settings)
            self.ssh_bookmark_check.setChecked(session.bookmark_settings)
            
        else:  # SFTP
            self.sftp_btn.click()
            self.sftp_host_input.setText(session.host)
            self.sftp_username_input.setText(session.username or "")
            self.sftp_port_input.setValue(session.port)
            self.sftp_bookmark_check.setChecked(session.bookmark_settings)
        
    def get_session_data(self) -> Session:
        if self.current_tab == "SSH":
            return Session(
                type='SSH',
                host=self.ssh_host_input.text(),
                port=self.ssh_port_input.value() if self.ssh_port_check.isChecked() else 22,
                username=self.ssh_username_input.text() if self.ssh_username_check.isChecked() else None,
                terminal_settings=self.ssh_terminal_check.isChecked(),
                network_settings=self.ssh_network_check.isChecked(),
                bookmark_settings=self.ssh_bookmark_check.isChecked()
            )
        else:
            return Session(
                type='SFTP',
                host=self.sftp_host_input.text(),
                port=self.sftp_port_input.value(),
                username=self.sftp_username_input.text(),
                bookmark_settings=self.sftp_bookmark_check.isChecked()
            )