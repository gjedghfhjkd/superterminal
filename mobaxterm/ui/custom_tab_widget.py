from PyQt5.QtWidgets import (QTabWidget, QWidget, QHBoxLayout, QLabel, 
                             QPushButton, QStyle, QStyleOptionTab, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor

class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setStyleSheet("""
            CloseButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                color: rgba(0, 0, 0, 0.35); /* faint cross by default */
                font-size: 12px;
                font-weight: bold;
            }
            CloseButton:hover {
                background-color: #ff4757; /* red square appears on hover */
                color: white; /* cross becomes prominent */
                border-radius: 3px;
                border: 1px solid rgba(255, 71, 87, 0.65); /* subtle red highlight */
            }
            CloseButton:pressed {
                background-color: #e03a49;
                border: 1px solid rgba(224, 58, 73, 0.75);
            }
        """)
        self.setText("×")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Close")
        # Prepare subtle red glow effect (disabled by default)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(255, 71, 87, 0))
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        # On hover: show a faint red glow around the square
        try:
            self._shadow.setBlurRadius(12)
            self._shadow.setColor(QColor(255, 71, 87, 140))
            self._shadow.setOffset(0, 0)
        except Exception:
            pass
        return super().enterEvent(event)

    def leaveEvent(self, event):
        # Remove glow when mouse leaves
        try:
            self._shadow.setBlurRadius(0)
            self._shadow.setColor(QColor(255, 71, 87, 0))
        except Exception:
            pass
        return super().leaveEvent(event)

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