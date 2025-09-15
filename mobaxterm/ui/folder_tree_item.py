from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

class FolderTreeItem(QWidget):
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.is_expanded = True
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # Expand/collapse button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(16, 16)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 8px;
                color: #666;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #999;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_folder)
        
        # Folder icon and name
        self.folder_icon = QLabel("📁")
        self.folder_icon.setFixedWidth(20)
        
        self.name_label = QLabel(self.folder_name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #0078d7;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.folder_icon)
        layout.addWidget(self.name_label)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def toggle_folder(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.toggle_btn.setText("▼")
        else:
            self.toggle_btn.setText("▶")
        
    def set_expanded(self, expanded):
        self.is_expanded = expanded
        if self.is_expanded:
            self.toggle_btn.setText("▼")
        else:
            self.toggle_btn.setText("▶")