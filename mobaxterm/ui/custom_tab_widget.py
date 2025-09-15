from PyQt5.QtWidgets import (QTabWidget, QWidget, QHBoxLayout, QLabel, 
                             QPushButton, QStyle, QStyleOptionTab)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter

class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setStyleSheet("""
            CloseButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #666;
                font-size: 12px;
                font-weight: bold;
            }
            CloseButton:hover {
                background-color: #ff4757;
                color: white;
            }
        """)
        self.setText("×")

class CustomTabWidget(QTabWidget):
    tab_close_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.on_tab_close)
        
        # Устанавливаем стили для отображения крестиков
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-top: none;
                background: white;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #ccc;
                border-bottom-color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
            }
        """)
    
    def on_tab_close(self, index):
        self.tab_close_requested.emit(index)