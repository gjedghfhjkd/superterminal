from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class SessionItemWidget(QWidget):
    delete_clicked = pyqtSignal()
    
    def __init__(self, session_name, parent=None):
        super().__init__(parent)
        self.session_name = session_name
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Session name label
        self.name_label = QLabel(self.session_name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 10px;
                background: transparent;
            }
        """)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Spacer
        layout.addWidget(self.name_label, 1)
        
        # Delete button
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(16, 16)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999;
                border: none;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff4757;
                color: white;
            }
        """)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self.delete_clicked.emit)
        
        layout.addWidget(self.delete_btn)
        
        self.setLayout(layout)