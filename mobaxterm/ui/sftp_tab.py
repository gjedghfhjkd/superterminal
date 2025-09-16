from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
import os
import time


class SFTPTab(QWidget):
    # UI -> Thread
    remote_change_dir = pyqtSignal(str)
    remote_up_dir = pyqtSignal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.session_index = None
        self._remote_path = '/'
        self._local_path = os.path.expanduser('~')
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Left (Local) panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(4)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_top = QWidget()
        left_top_layout = QHBoxLayout(left_top)
        left_top_layout.setSpacing(6)
        left_top_layout.setContentsMargins(6, 6, 6, 6)
        left_label = QLabel("Local:")
        self.local_up_btn = QPushButton("↑")
        self.local_path_edit = QLineEdit(self._local_path)
        left_top_layout.addWidget(left_label)
        left_top_layout.addWidget(self.local_up_btn)
        left_top_layout.addWidget(self.local_path_edit, 1)

        self.local_tree = QTreeWidget()
        self.local_tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.local_tree.setColumnWidth(0, 280)
        self.local_tree.setAlternatingRowColors(True)

        left_layout.addWidget(left_top)
        left_layout.addWidget(self.local_tree)

        # Right (Remote) panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(4)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_top = QWidget()
        right_top_layout = QHBoxLayout(right_top)
        right_top_layout.setSpacing(6)
        right_top_layout.setContentsMargins(6, 6, 6, 6)
        right_label = QLabel("Remote:")
        self.remote_up_btn = QPushButton("↑")
        self.remote_path_edit = QLineEdit(self._remote_path)
        right_top_layout.addWidget(right_label)
        right_top_layout.addWidget(self.remote_up_btn)
        right_top_layout.addWidget(self.remote_path_edit, 1)

        self.remote_tree = QTreeWidget()
        self.remote_tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.remote_tree.setColumnWidth(0, 280)
        self.remote_tree.setAlternatingRowColors(True)

        right_layout.addWidget(right_top)
        right_layout.addWidget(self.remote_tree)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])

        layout.addWidget(splitter)

        # Wire local events
        self.local_up_btn.clicked.connect(self.on_local_up)
        self.local_path_edit.returnPressed.connect(self.on_local_path_enter)
        self.local_tree.itemDoubleClicked.connect(self.on_local_item_double_clicked)

        # Wire remote events
        self.remote_up_btn.clicked.connect(lambda: self.remote_up_dir.emit())
        self.remote_path_edit.returnPressed.connect(self.on_remote_path_enter)
        self.remote_tree.itemDoubleClicked.connect(self.on_remote_item_double_clicked)

        # Initial local listing
        self._populate_local()

    # ===== Local side =====
    def _list_local(self, path):
        try:
            names = os.listdir(path)
        except Exception:
            return []
        entries = []
        for name in names:
            full = os.path.join(path, name)
            try:
                st = os.stat(full)
                is_dir = os.path.isdir(full)
                entries.append({
                    'name': name,
                    'is_dir': is_dir,
                    'size': st.st_size,
                    'mtime': st.st_mtime,
                })
            except Exception:
                continue
        entries.sort(key=lambda e: (0 if e['is_dir'] else 1, e['name'].lower()))
        return entries

    def _fmt_size(self, size):
        try:
            for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
                if size < 1024:
                    return f"{size:.0f} {unit}"
                size /= 1024.0
            return f"{size:.0f} PB"
        except Exception:
            return ""

    def _fmt_time(self, ts):
        try:
            return time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        except Exception:
            return ""

    def _populate_local(self):
        self.local_tree.clear()
        self.local_path_edit.setText(self._local_path)
        entries = self._list_local(self._local_path)
        # Add parent dir entry ..
        if self._local_path not in ('/', ''):
            up_item = QTreeWidgetItem(["..", "", ""])
            up_item.setData(0, Qt.UserRole, {'name': '..', 'is_dir': True})
            self.local_tree.addTopLevelItem(up_item)
        for e in entries:
            name = ("📁 " if e['is_dir'] else "📄 ") + e['name']
            size = "" if e['is_dir'] else self._fmt_size(e['size'])
            mtime = self._fmt_time(e['mtime'])
            it = QTreeWidgetItem([name, size, mtime])
            it.setData(0, Qt.UserRole, e)
            self.local_tree.addTopLevelItem(it)
        self.local_tree.sortItems(0, Qt.AscendingOrder)

    def on_local_up(self):
        parent = os.path.dirname(self._local_path.rstrip(os.sep)) or os.sep
        self._local_path = parent
        self._populate_local()

    def on_local_path_enter(self):
        path = self.local_path_edit.text().strip()
        if os.path.isdir(path):
            self._local_path = path
            self._populate_local()

    def on_local_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        name = data.get('name')
        is_dir = data.get('is_dir')
        if name == '..':
            self.on_local_up()
            return
        if is_dir:
            self._local_path = os.path.join(self._local_path, name)
            self._populate_local()

    # ===== Remote side =====
    def set_remote_listing(self, path, entries):
        self._remote_path = path or '/'
        self.remote_tree.clear()
        self.remote_path_edit.setText(self._remote_path)
        # Add parent dir entry .. when not at root
        if self._remote_path not in ('/', ''):
            up_item = QTreeWidgetItem(["..", "", ""])
            up_item.setData(0, Qt.UserRole, {'name': '..', 'is_dir': True})
            self.remote_tree.addTopLevelItem(up_item)
        for e in entries or []:
            name = ("📁 " if e.get('is_dir') else "📄 ") + e.get('name', '')
            size = "" if e.get('is_dir') else self._fmt_size(e.get('size', 0))
            mtime = self._fmt_time(e.get('mtime', 0))
            it = QTreeWidgetItem([name, size, mtime])
            it.setData(0, Qt.UserRole, e)
            self.remote_tree.addTopLevelItem(it)
        self.remote_tree.sortItems(0, Qt.AscendingOrder)

    def on_remote_path_enter(self):
        path = self.remote_path_edit.text().strip()
        if path:
            self.remote_change_dir.emit(path)

    def on_remote_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        name = data.get('name')
        is_dir = data.get('is_dir')
        if name == '..':
            self.remote_up_dir.emit()
            return
        if is_dir:
            # Build new path relative to current
            if self._remote_path.endswith('/'):
                new_path = self._remote_path + name
            else:
                new_path = self._remote_path + '/' + name
            self.remote_change_dir.emit(new_path)

