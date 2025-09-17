from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
							  QTableWidget, QTableWidgetItem, QWidget, QLineEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
from ..core.session_manager import SessionManager
from ..core.tunneling import port_forward_manager
from ..models.session import Session

class TunnelingDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("SSH Tunneling")
		self.setModal(True)
		self.resize(640, 420)
		self.session_manager = getattr(parent, 'session_manager', SessionManager())
		self._forwards = []  # in-memory definitions; extend to persistence if needed
		self._init_ui()
		# Allow backend to resolve sessions by index
		try:
			port_forward_manager.set_session_resolver(self.session_manager.get_session)
		except Exception:
			pass

	def _init_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(10, 10, 10, 10)
		layout.setSpacing(8)

		# Header
		header = QLabel("Manage SSH port forwarding (local/remote)")
		header.setStyleSheet("font-weight: bold; font-size: 15px; color: #333;")
		layout.addWidget(header)

		# Table of forwards
		self.table = QTableWidget(0, 6)
		self.table.setHorizontalHeaderLabels(["Type", "Session", "Bind Host", "Bind Port", "Target Host", "Target Port"])
		self.table.horizontalHeader().setStretchLastSection(True)
		layout.addWidget(self.table)

		# Editor row
		row = QWidget()
		row_layout = QHBoxLayout(row)
		row_layout.setContentsMargins(0, 0, 0, 0)
		row_layout.setSpacing(6)

		self.cmb_type = QComboBox()
		self.cmb_type.addItems(["Local", "Remote"])  # Local: -L, Remote: -R
		row_layout.addWidget(self.cmb_type)

		self.cmb_session = QComboBox()
		sessions = self.session_manager.get_all_sessions()
		for i, s in enumerate(sessions):
			name = getattr(s, 'name', None) or s.host
			self.cmb_session.addItem(f"{name}", i)
		row_layout.addWidget(self.cmb_session)

		self.ed_bind_host = QLineEdit("127.0.0.1")
		self.ed_bind_host.setPlaceholderText("Bind host")
		self.ed_bind_host.setFixedWidth(120)
		row_layout.addWidget(self.ed_bind_host)

		self.ed_bind_port = QLineEdit("")
		self.ed_bind_port.setPlaceholderText("Bind port")
		self.ed_bind_port.setFixedWidth(90)
		row_layout.addWidget(self.ed_bind_port)

		self.ed_target_host = QLineEdit("")
		self.ed_target_host.setPlaceholderText("Target host")
		self.ed_target_host.setFixedWidth(160)
		row_layout.addWidget(self.ed_target_host)

		self.ed_target_port = QLineEdit("")
		self.ed_target_port.setPlaceholderText("Target port")
		self.ed_target_port.setFixedWidth(90)
		row_layout.addWidget(self.ed_target_port)

		btn_add = QPushButton("Add")
		btn_add.clicked.connect(self._on_add_forward)
		row_layout.addWidget(btn_add)

		layout.addWidget(row)

		# React to type changes to hide/show Target Host for Local/Remote
		self.cmb_type.currentTextChanged.connect(self._on_type_changed)
		self._on_type_changed(self.cmb_type.currentText())

		# Actions
		actions = QWidget()
		actions_layout = QHBoxLayout(actions)
		actions_layout.setContentsMargins(0, 0, 0, 0)
		actions_layout.setSpacing(6)

		self.btn_start = QPushButton("Start Selected")
		self.btn_stop = QPushButton("Stop Selected")
		self.btn_close = QPushButton("Close")
		self.btn_start.clicked.connect(self._start_selected)
		self.btn_stop.clicked.connect(self._stop_selected)
		self.btn_close.clicked.connect(self.accept)

		actions_layout.addWidget(self.btn_start)
		actions_layout.addWidget(self.btn_stop)
		actions_layout.addStretch()
		actions_layout.addWidget(self.btn_close)
		layout.addWidget(actions)

	def _on_add_forward(self):
		try:
			forward_type = self.cmb_type.currentText()
			idx = self.cmb_session.currentData()
			session = self.session_manager.get_session(idx)
			bind_host = self.ed_bind_host.text().strip() or "127.0.0.1"
			bind_port = int(self.ed_bind_port.text().strip())
			# For Local forwarding, use selected session host as target host
			if forward_type == "Local":
				target_host = getattr(session, 'host', '')
			else:
				target_host = self.ed_target_host.text().strip()
			target_port = int(self.ed_target_port.text().strip())
			if forward_type == "Remote" and not target_host:
				QMessageBox.warning(self, "Validation", "Target host is required")
				return
			if bind_port <= 0 or target_port <= 0:
				QMessageBox.warning(self, "Validation", "Ports must be positive integers")
				return
			self._forwards.append({
				"type": forward_type,
				"session_index": idx,
				"bind_host": bind_host,
				"bind_port": bind_port,
				"target_host": target_host,
				"target_port": target_port,
				"status": "stopped"
			})
			self._refresh_table()
		except ValueError:
			QMessageBox.warning(self, "Validation", "Ports must be integers")

	def _on_type_changed(self, text: str):
		# Hide Target Host for Local tunnels; show for Remote
		is_local = (text == "Local")
		self.ed_target_host.setVisible(not is_local)

	def _refresh_table(self):
		self.table.setRowCount(len(self._forwards))
		for r, fwd in enumerate(self._forwards):
			self.table.setItem(r, 0, QTableWidgetItem(fwd["type"]))
			s = self.session_manager.get_session(fwd["session_index"]) or Session(host="?")
			name = getattr(s, 'name', None) or s.host
			self.table.setItem(r, 1, QTableWidgetItem(name))
			self.table.setItem(r, 2, QTableWidgetItem(fwd["bind_host"]))
			self.table.setItem(r, 3, QTableWidgetItem(str(fwd["bind_port"])))
			self.table.setItem(r, 4, QTableWidgetItem(fwd["target_host"]))
			self.table.setItem(r, 5, QTableWidgetItem(str(fwd["target_port"])))

	def _selected_rows(self):
		rows = set()
		for idx in self.table.selectedIndexes():
			rows.add(idx.row())
		return sorted(rows)

	def _start_selected(self):
		rows = self._selected_rows()
		if not rows:
			QMessageBox.information(self, "Tunneling", "Select at least one row")
			return
		# Start each selected forward via backend
		for r in rows:
			f = self._forwards[r]
			try:
				if f.get("status") == "running" and f.get("id"):
					continue
				if f["type"] == "Local":
					fid = port_forward_manager.start_local_forward(
						f["session_index"], f["bind_host"], f["bind_port"], f["target_host"], f["target_port"]
					)
				else:
					fid = port_forward_manager.start_remote_forward(
						f["session_index"], f["bind_host"], f["bind_port"], f["target_host"], f["target_port"]
					)
				f["id"] = fid
				f["status"] = "running"
			except Exception as e:
				QMessageBox.warning(self, "Tunneling", f"Failed to start: {e}")
		self._refresh_table()

	def _stop_selected(self):
		rows = self._selected_rows()
		if not rows:
			QMessageBox.information(self, "Tunneling", "Select at least one row")
			return
		# Stop each selected forward via backend
		for r in rows:
			f = self._forwards[r]
			fid = f.get("id")
			if not fid:
				continue
			try:
				port_forward_manager.stop_forward(fid)
				f["status"] = "stopped"
				f.pop("id", None)
			except Exception as e:
				QMessageBox.warning(self, "Tunneling", f"Failed to stop: {e}")
		self._refresh_table()