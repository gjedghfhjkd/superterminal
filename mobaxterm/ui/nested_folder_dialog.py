from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem)
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
        
        # Parent folder selection
        parent_label = QLabel("Parent folder:")
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("(Root)", "")
        for folder in self.existing_folders:
            self.parent_combo.addItem(folder, folder)
        
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