from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QCheckBox, QSpinBox, QGroupBox,

                             QDialogButtonBox, QGridLayout, QStackedWidget, QWidget, QComboBox,
                             QFileDialog, QInputDialog, QSizePolicy, QListView, QStyledItemDelegate, QStyle, QAbstractItemView, QStyleOptionViewItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

class SolidHighlightDelegate(QStyledItemDelegate):
    def __init__(self, highlight_color="#0078d7", text_color="#ffffff", parent=None):
        super().__init__(parent)
        self.highlight_color = QColor(highlight_color)
        self.text_color = QColor(text_color)

    def paint(self, painter, option, index):
        option_clone = QStyleOptionViewItem(option)
        painter.save()
        if option_clone.state & QStyle.State_Selected:
            painter.fillRect(option_clone.rect, self.highlight_color)
            option_clone.palette.setColor(QPalette.Text, self.text_color)
            option_clone.palette.setColor(QPalette.HighlightedText, self.text_color)
        super().paint(painter, option_clone, index)
        painter.restore()
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
            /* Improve dropdown (popup) visibility for all combo boxes */
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 6px;
                color: #333;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e9f3ff;
                color: #0a58ca;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0078d7;
                color: white;
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
        
        # Removed bottom session type label per requirements
        
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
        
        # Row 1: Session name (optional, defaults to Remote host)
        name_label = QLabel("Session name:")
        name_label.setMinimumWidth(100)
        basic_layout.addWidget(name_label, 1, 0, Qt.AlignRight)
        
        self.ssh_name_input = QLineEdit()
        self.ssh_name_input.setPlaceholderText("defaults to Remote host")
        self.ssh_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_name_input, 1, 1)
        
        # Row 2: Username label and input (always enabled)
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        basic_layout.addWidget(username_label, 2, 0, Qt.AlignRight)
        
        self.ssh_username_input = QLineEdit()
        self.ssh_username_input.setPlaceholderText("username")
        self.ssh_username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Default username to root
        self.ssh_username_input.setText("root")
        basic_layout.addWidget(self.ssh_username_input, 2, 1)
        
        
        # Row 3: Port label and input
        port_label = QLabel("Port:")
        port_label.setMinimumWidth(100)
        basic_layout.addWidget(port_label, 3, 0, Qt.AlignRight)
        
        self.ssh_port_input = QSpinBox()
        self.ssh_port_input.setRange(1, 65535)
        self.ssh_port_input.setValue(22)
        self.ssh_port_input.setEnabled(True)
        self.ssh_port_input.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        basic_layout.addWidget(self.ssh_port_input, 3, 1)
        
        # Row 4: Folder label and combo
        folder_label = QLabel("Folder:")
        folder_label.setMinimumWidth(100)
        basic_layout.addWidget(folder_label, 4, 0, Qt.AlignRight)
        
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("(No folder)", None)
        
        # Load existing folders
        if self.parent and hasattr(self.parent, 'session_manager'):
            folders = self.parent.session_manager.get_all_folders()
            for folder in folders:
                self.folder_combo.addItem(folder, folder)
        
        self.folder_combo.addItem("+ Create new folder...", "new")
        basic_layout.addWidget(self.folder_combo, 4, 1)
        # Ensure dropdown selection is visible for folder combo
        folder_view = QListView()
        folder_view.setUniformItemSizes(True)
        folder_view.setStyleSheet("""
            QListView {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                selection-background-color: #0078d7;
                selection-color: white;
                outline: 0;
            }
            QListView::item { height: 28px; padding: 6px; }
            QListView::item:hover { background-color: #e9f3ff; color: #0a58ca; }
            QListView::item:selected { background-color: #0078d7; color: white; }
        """)
        folder_palette = folder_view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            folder_palette.setColor(group, QPalette.Highlight, QColor("#0078d7"))
            folder_palette.setColor(group, QPalette.HighlightedText, QColor("#ffffff"))
        folder_view.setPalette(folder_palette)
        folder_view.setItemDelegate(SolidHighlightDelegate(parent=folder_view))
        self.folder_combo.setView(folder_view)
        
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
        # Ensure dropdown selection is visible for auth method combo
        auth_view = QListView()
        auth_view.setUniformItemSizes(True)
        auth_view.setStyleSheet("""
            QListView {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                selection-background-color: #0078d7;
                selection-color: white;
                outline: 0;
            }
            QListView::item { height: 28px; padding: 6px; }
            QListView::item:hover { background-color: #e9f3ff; color: #0a58ca; }
            QListView::item:selected { background-color: #0078d7; color: white; }
        """)
        auth_palette = auth_view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            auth_palette.setColor(group, QPalette.Highlight, QColor("#0078d7"))
            auth_palette.setColor(group, QPalette.HighlightedText, QColor("#ffffff"))
        auth_view.setPalette(auth_palette)
        auth_view.setItemDelegate(SolidHighlightDelegate(parent=auth_view))
        self.auth_method_combo.setView(auth_view)

        # Row 1: Password (for password auth)
        self.auth_password_label = QLabel("Password:")
        self.auth_password_label.setMinimumWidth(100)
        auth_layout.addWidget(self.auth_password_label, 1, 0, Qt.AlignRight)
        self.auth_password_input = QLineEdit()
        self.auth_password_input.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.auth_password_input, 1, 1)

        # Row 2: Private key path (for key auth)
        self.key_path_label = QLabel("Private key:")
        self.key_path_label.setMinimumWidth(100)
        auth_layout.addWidget(self.key_path_label, 2, 0, Qt.AlignRight)

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
        auth_layout.addWidget(key_path_container, 2, 1)

        # Row 3: Passphrase (for key auth)
        self.passphrase_label = QLabel("Passphrase:")
        self.passphrase_label.setMinimumWidth(100)
        auth_layout.addWidget(self.passphrase_label, 3, 0, Qt.AlignRight)

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.passphrase_input, 3, 1)

        layout.addWidget(auth_group)

        # Removed Advanced SSH settings group per requirements
        layout.addStretch()
        
        # Connect signals
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
        
        # Row 1: Session name (optional, defaults to Remote host)
        sftp_name_label = QLabel("Session name:")
        sftp_name_label.setMinimumWidth(100)
        basic_layout.addWidget(sftp_name_label, 1, 0, Qt.AlignRight)
        
        self.sftp_name_input = QLineEdit()
        self.sftp_name_input.setPlaceholderText("defaults to Remote host")
        self.sftp_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        basic_layout.addWidget(self.sftp_name_input, 1, 1)
        
        # Row 2: Username
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        basic_layout.addWidget(username_label, 2, 0, Qt.AlignRight)
        
        self.sftp_username_input = QLineEdit()
        self.sftp_username_input.setPlaceholderText("username")
        self.sftp_username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Default username to root
        self.sftp_username_input.setText("root")
        basic_layout.addWidget(self.sftp_username_input, 2, 1)
        
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
        # Ensure dropdown selection is visible for sftp folder combo
        sftp_view = QListView()
        sftp_view.setUniformItemSizes(True)
        sftp_view.setStyleSheet("""
            QListView {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                selection-background-color: #0078d7;
                selection-color: white;
                outline: 0;
            }
            QListView::item { height: 28px; padding: 6px; }
            QListView::item:hover { background-color: #e9f3ff; color: #0a58ca; }
            QListView::item:selected { background-color: #0078d7; color: white; }
        """)
        sftp_palette = sftp_view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            sftp_palette.setColor(group, QPalette.Highlight, QColor("#0078d7"))
            sftp_palette.setColor(group, QPalette.HighlightedText, QColor("#ffffff"))
        sftp_view.setPalette(sftp_palette)
        sftp_view.setItemDelegate(SolidHighlightDelegate(parent=sftp_view))
        self.sftp_folder_combo.setView(sftp_view)
        
        layout.addWidget(basic_group)

        # Authentication group for SFTP
        sftp_auth_group = QGroupBox("Authentication")
        sftp_auth_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sftp_auth_layout = QGridLayout(sftp_auth_group)
        sftp_auth_layout.setSpacing(8)
        sftp_auth_layout.setContentsMargins(12, 15, 12, 12)
        sftp_auth_layout.setColumnStretch(0, 0)
        sftp_auth_layout.setColumnStretch(1, 1)

        # Row 0: Method
        sftp_auth_method_label = QLabel("Method:")
        sftp_auth_method_label.setMinimumWidth(100)
        sftp_auth_layout.addWidget(sftp_auth_method_label, 0, 0, Qt.AlignRight)

        self.sftp_auth_method_combo = QComboBox()
        self.sftp_auth_method_combo.addItem("Password", "password")
        self.sftp_auth_method_combo.addItem("SSH key", "key")
        sftp_auth_layout.addWidget(self.sftp_auth_method_combo, 0, 1)
        # Ensure dropdown selection is visible for SFTP auth method combo
        sftp_auth_view = QListView()
        sftp_auth_view.setUniformItemSizes(True)
        sftp_auth_view.setStyleSheet("""
            QListView {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                selection-background-color: #0078d7;
                selection-color: white;
                outline: 0;
            }
            QListView::item { height: 28px; padding: 6px; }
            QListView::item:hover { background-color: #e9f3ff; color: #0a58ca; }
            QListView::item:selected { background-color: #0078d7; color: white; }
        """)
        sftp_auth_palette = sftp_auth_view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            sftp_auth_palette.setColor(group, QPalette.Highlight, QColor("#0078d7"))
            sftp_auth_palette.setColor(group, QPalette.HighlightedText, QColor("#ffffff"))
        sftp_auth_view.setPalette(sftp_auth_palette)
        sftp_auth_view.setItemDelegate(SolidHighlightDelegate(parent=sftp_auth_view))
        self.sftp_auth_method_combo.setView(sftp_auth_view)

        # Row 1: Password (for password auth)
        self.sftp_auth_password_label = QLabel("Password:")
        self.sftp_auth_password_label.setMinimumWidth(100)
        sftp_auth_layout.addWidget(self.sftp_auth_password_label, 1, 0, Qt.AlignRight)
        self.sftp_auth_password_input = QLineEdit()
        self.sftp_auth_password_input.setEchoMode(QLineEdit.Password)
        sftp_auth_layout.addWidget(self.sftp_auth_password_input, 1, 1)

        # Row 2: Private key path (for key auth)
        self.sftp_key_path_label = QLabel("Private key:")
        self.sftp_key_path_label.setMinimumWidth(100)
        sftp_auth_layout.addWidget(self.sftp_key_path_label, 2, 0, Qt.AlignRight)

        sftp_key_path_container = QWidget()
        sftp_key_path_h = QHBoxLayout(sftp_key_path_container)
        sftp_key_path_h.setContentsMargins(0, 0, 0, 0)
        sftp_key_path_h.setSpacing(6)
        self.sftp_key_path_input = QLineEdit()
        self.sftp_key_path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sftp_key_path_browse = QPushButton("Browse…")
        self.sftp_key_path_browse.setFixedWidth(90)
        sftp_key_path_h.addWidget(self.sftp_key_path_input)
        sftp_key_path_h.addWidget(self.sftp_key_path_browse)
        sftp_auth_layout.addWidget(sftp_key_path_container, 2, 1)

        # Row 3: Passphrase (for key auth)
        self.sftp_passphrase_label = QLabel("Passphrase:")
        self.sftp_passphrase_label.setMinimumWidth(100)
        sftp_auth_layout.addWidget(self.sftp_passphrase_label, 3, 0, Qt.AlignRight)

        self.sftp_passphrase_input = QLineEdit()
        self.sftp_passphrase_input.setEchoMode(QLineEdit.Password)
        sftp_auth_layout.addWidget(self.sftp_passphrase_input, 3, 1)

        layout.addWidget(sftp_auth_group)
        
        advanced_group = QGroupBox("Advanced SFTP settings")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(8)
        advanced_layout.setContentsMargins(12, 15, 12, 12)
        
        self.sftp_bookmark_check = QCheckBox("Bookmark settings")
        advanced_layout.addWidget(self.sftp_bookmark_check)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        self.sftp_folder_combo.currentIndexChanged.connect(self.on_sftp_folder_changed)
        self.sftp_auth_method_combo.currentIndexChanged.connect(self.on_sftp_auth_method_changed)
        self.sftp_key_path_browse.clicked.connect(self.on_sftp_browse_key)
        # Initialize SFTP auth controls state
        self.on_sftp_auth_method_changed(self.sftp_auth_method_combo.currentIndex())
        
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
        
    def switch_to_sftp(self):
        self.current_tab = "SFTP"
        self.sftp_btn.setChecked(True)
        self.ssh_btn.setChecked(False)
        
        self.sftp_btn.setStyleSheet(self.get_tab_style(True))
        self.ssh_btn.setStyleSheet(self.get_tab_style(False))
        
        self.stacked_widget.setCurrentIndex(1)
        
    def load_session_data(self, session: Session):
        if session.type == 'SSH':
            self.ssh_btn.click()
            self.ssh_host_input.setText(session.host)
            # Load session name (fallback to host)
            self.ssh_name_input.setText(session.name or session.host)
            
            if session.username:
                self.ssh_username_input.setText(session.username)
            
            self.ssh_port_input.setValue(session.port)
            
            if session.folder:
                index = self.folder_combo.findData(session.folder)
                if index >= 0:
                    self.folder_combo.setCurrentIndex(index)
            
            # Load auth
            if hasattr(session, 'auth_method'):
                method_index = self.auth_method_combo.findData(session.auth_method)
                if method_index >= 0:
                    self.auth_method_combo.setCurrentIndex(method_index)
            # Populate auth fields
            if getattr(session, 'auth_method', 'password') == 'password' and getattr(session, 'password', None):
                self.auth_password_input.setText(session.password)
            if hasattr(session, 'private_key_path') and session.private_key_path:
                self.key_path_input.setText(session.private_key_path)
            if hasattr(session, 'private_key_passphrase') and session.private_key_passphrase:
                self.passphrase_input.setText(session.private_key_passphrase)
            
        else:
            self.sftp_btn.click()
            self.sftp_host_input.setText(session.host)
            # Load session name (fallback to host)
            self.sftp_name_input.setText(session.name or session.host)
            self.sftp_username_input.setText(session.username or "")
            self.sftp_port_input.setValue(session.port)
            # Load SFTP auth
            if hasattr(session, 'auth_method'):
                sftp_method_index = self.sftp_auth_method_combo.findData(session.auth_method)
                if sftp_method_index >= 0:
                    self.sftp_auth_method_combo.setCurrentIndex(sftp_method_index)
            if getattr(session, 'auth_method', 'password') == 'password' and getattr(session, 'password', None):
                self.sftp_auth_password_input.setText(session.password)
            if hasattr(session, 'private_key_path') and session.private_key_path:
                self.sftp_key_path_input.setText(session.private_key_path)
            if hasattr(session, 'private_key_passphrase') and session.private_key_passphrase:
                self.sftp_passphrase_input.setText(session.private_key_passphrase)
            
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
                port=self.ssh_port_input.value(),
                name=(self.ssh_name_input.text().strip() or None),
                username=(self.ssh_username_input.text() or None),
                auth_method=self.auth_method_combo.currentData(),
                private_key_path=self.key_path_input.text() if self.auth_method_combo.currentData() == 'key' and self.key_path_input.text() else None,
                private_key_passphrase=self.passphrase_input.text() if self.auth_method_combo.currentData() == 'key' and self.passphrase_input.text() else None
            )
            # Set password only for password auth
            if self.auth_method_combo.currentData() == 'password':
                session.password = self.auth_password_input.text()
            session.folder = self.folder_combo.currentData()
            return session
        else:
            session = Session(
                type='SFTP',
                host=self.sftp_host_input.text(),
                port=self.sftp_port_input.value(),
                name=(self.sftp_name_input.text().strip() or None),
                username=self.sftp_username_input.text(),
                auth_method=self.sftp_auth_method_combo.currentData(),
                private_key_path=self.sftp_key_path_input.text() if self.sftp_auth_method_combo.currentData() == 'key' and self.sftp_key_path_input.text() else None,
                private_key_passphrase=self.sftp_passphrase_input.text() if self.sftp_auth_method_combo.currentData() == 'key' and self.sftp_passphrase_input.text() else None,
                bookmark_settings=self.sftp_bookmark_check.isChecked()
            )
            if self.sftp_auth_method_combo.currentData() == 'password':
                session.password = self.sftp_auth_password_input.text()
            session.folder = self.sftp_folder_combo.currentData()
            return session

    def on_auth_method_changed(self, index):
        method = self.auth_method_combo.currentData()
        is_key = method == 'key'
        # Toggle visibility between password and key controls
        self.auth_password_label.setVisible(not is_key)
        self.auth_password_input.setVisible(not is_key)
        self.key_path_label.setVisible(is_key)
        self.key_path_input.setVisible(is_key)
        self.key_path_browse.setVisible(is_key)
        self.passphrase_label.setVisible(is_key)
        self.passphrase_input.setVisible(is_key)
        # Enable relevant fields
        self.key_path_input.setEnabled(is_key)
        self.key_path_browse.setEnabled(is_key)
        self.passphrase_input.setEnabled(is_key)

    def on_browse_key(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "All Files (*)")
        if file_path:
            self.key_path_input.setText(file_path)

    def on_sftp_auth_method_changed(self, index):
        method = self.sftp_auth_method_combo.currentData()
        is_key = method == 'key'
        # Toggle visibility between password and key controls
        self.sftp_auth_password_label.setVisible(not is_key)
        self.sftp_auth_password_input.setVisible(not is_key)
        self.sftp_key_path_label.setVisible(is_key)
        self.sftp_key_path_input.setVisible(is_key)
        self.sftp_key_path_browse.setVisible(is_key)
        self.sftp_passphrase_label.setVisible(is_key)
        self.sftp_passphrase_input.setVisible(is_key)
        # Enable relevant fields
        self.sftp_key_path_input.setEnabled(is_key)
        self.sftp_key_path_browse.setEnabled(is_key)
        self.sftp_passphrase_input.setEnabled(is_key)

    def on_sftp_browse_key(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "All Files (*)")
        if file_path:
            self.sftp_key_path_input.setText(file_path)