from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class FolderItemWidget(QWidget):
    delete_clicked = pyqtSignal(str)
    
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(8)
        
        # Folder icon and name
        self.name_label = QLabel(f"📁 {self.folder_name}")
        self.name_label.setStyleSheet("""
            QLabel {
                color: #0078d7;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Spacer
        layout.addWidget(self.name_label, 1)
        
        # Delete button
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff4757;
                color: white;
            }
        """)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.folder_name))
        
        layout.addWidget(self.delete_btn)
        
        self.setLayout(layout)