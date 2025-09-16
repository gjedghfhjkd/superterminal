from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem, QListView)
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class NestedFolderDialog(QDialog):
    def __init__(self, parent=None, existing_folders=None):
        super().__init__(parent)
        self.setWindowTitle("Create Nested Folder")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        self.existing_folders = existing_folders or []
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        # Improve dropdown selection contrast inside this dialog
        self.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
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
        
        # Parent folder selection
        parent_label = QLabel("Parent folder:")
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("(Root)", "")
        for folder in self.existing_folders:
            self.parent_combo.addItem(folder, folder)
        # Ensure dropdown selection is visible for parent folder combo
        parent_view = QListView()
        parent_view.setUniformItemSizes(True)
        parent_view.setStyleSheet("""
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
        parent_palette = parent_view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            parent_palette.setColor(group, QPalette.Highlight, QColor("#0078d7"))
            parent_palette.setColor(group, QPalette.HighlightedText, QColor("#ffffff"))
        parent_view.setPalette(parent_palette)
        self.parent_combo.setView(parent_view)
        
        # Folder name
        name_label = QLabel("Folder name:")
        self.name_input = QLineEdit()
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addWidget(parent_label)
        layout.addWidget(self.parent_combo)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addLayout(button_layout)
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
    
    def get_folder_path(self):
        parent_path = self.parent_combo.currentData()
        folder_name = self.name_input.text().strip()
        if not folder_name:
            return None
        if parent_path:
            return f"{parent_path}/{folder_name}"
        return folder_name