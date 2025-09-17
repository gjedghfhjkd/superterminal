from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
							  QTableWidget, QTableWidgetItem, QWidget, QLineEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import os
import json
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
		self._config_file = "tunnels.json"
		self._init_ui()
		# Allow backend to resolve sessions by index
		try:
			port_forward_manager.set_session_resolver(self.session_manager.get_session)
		except Exception:
			pass
		# Load saved tunnels from disk
		try:
			self._load_tunnels()
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
		self.table = QTableWidget(0, 8)
		self.table.setHorizontalHeaderLabels(["Name", "Type", "Start/Stop", "Session", "Bind Host", "Bind Port", "Target Host", "Target Port"])
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

		# Tunnel name
		self.ed_name = QLineEdit("")
		self.ed_name.setPlaceholderText("Tunnel name (optional)")
		self.ed_name.setFixedWidth(180)
		row_layout.addWidget(self.ed_name)

		self.cmb_session = QComboBox()
		sessions = self.session_manager.get_all_sessions()
		for i, s in enumerate(sessions):
			# Only allow SSH sessions in tunneling
			try:
				stype = getattr(s, 'type', None)
				if stype != 'SSH':
					continue
			except Exception:
				continue
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

		self.btn_start = QPushButton("▶ Start All")
		self.btn_stop = QPushButton("⏹ Stop All")
		self.btn_close = QPushButton("Close")
		self.btn_start.clicked.connect(self._start_all)
		self.btn_stop.clicked.connect(self._stop_all)
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
			# Determine display name (empty by default if not provided)
			name = self.ed_name.text().strip()
			self._forwards.append({
				"name": name,
				"type": forward_type,
				"session_index": idx,
				"bind_host": bind_host,
				"bind_port": bind_port,
				"target_host": target_host,
				"target_port": target_port,
				"status": "stopped"
			})
			self._refresh_table()
			self._save_tunnels()
		except ValueError:
			QMessageBox.warning(self, "Validation", "Ports must be integers")

	def _on_type_changed(self, text: str):
		# Hide Target Host for Local tunnels; show for Remote
		is_local = (text == "Local")
		self.ed_target_host.setVisible(not is_local)

	def _refresh_table(self):
		self.table.setRowCount(len(self._forwards))
		for r, fwd in enumerate(self._forwards):
			# Name
			self.table.setItem(r, 0, QTableWidgetItem(fwd.get("name", "")))
			# Type
			self.table.setItem(r, 1, QTableWidgetItem(fwd["type"]))
			# Start/Stop actions (placed right of Type)
			actions_widget = self._make_actions_widget(r, fwd.get("status") == "running")
			self.table.setCellWidget(r, 2, actions_widget)
			# Session display
			s = self.session_manager.get_session(fwd["session_index"]) or Session(host="?")
			s_name = getattr(s, 'name', None) or s.host
			self.table.setItem(r, 3, QTableWidgetItem(s_name))
			# Bind host/port
			self.table.setItem(r, 4, QTableWidgetItem(fwd["bind_host"]))
			self.table.setItem(r, 5, QTableWidgetItem(str(fwd["bind_port"])))
			# Target host/port
			self.table.setItem(r, 6, QTableWidgetItem(fwd["target_host"]))
			self.table.setItem(r, 7, QTableWidgetItem(str(fwd["target_port"])))

	def _selected_rows(self):
		rows = set()
		for idx in self.table.selectedIndexes():
			rows.add(idx.row())
		return sorted(rows)

	def _make_actions_widget(self, row_index: int, is_running: bool) -> QWidget:
		w = QWidget()
		lay = QHBoxLayout(w)
		lay.setContentsMargins(0, 0, 0, 0)
		lay.setSpacing(4)
		# Status indicator (blinking dot when running)
		indicator = QLabel("●")
		indicator.setFixedWidth(14)
		indicator.setAlignment(Qt.AlignCenter)
		lay.addWidget(indicator)
		btn_start = QPushButton("▶")
		btn_stop = QPushButton("⏹")
		btn_start.setFixedWidth(28)
		btn_stop.setFixedWidth(28)
		btn_start.setEnabled(not is_running)
		btn_stop.setEnabled(is_running)
		btn_start.clicked.connect(lambda: self._start_row(row_index))
		btn_stop.clicked.connect(lambda: self._stop_row(row_index))
		lay.addWidget(btn_start)
		lay.addWidget(btn_stop)
		lay.addStretch()
		# Blink setup
		if is_running:
			indicator.setStyleSheet("color: #28a745;")
			try:
				blink = QTimer(w)
				blink.setInterval(500)
				state = {"on": True}
				def toggle():
					state["on"] = not state["on"]
					indicator.setStyleSheet("color: #28a745;" if state["on"] else "color: #7ddc9a;")
				blink.timeout.connect(toggle)
				blink.start()
			except Exception:
				pass
		else:
			indicator.setStyleSheet("color: #bbbbbb;")
		return w

	def _start_row(self, r: int):
		if r < 0 or r >= len(self._forwards):
			return
		f = self._forwards[r]
		try:
			if f.get("status") == "running" and f.get("id"):
				return
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
		self._save_tunnels()

	def _stop_row(self, r: int):
		if r < 0 or r >= len(self._forwards):
			return
		f = self._forwards[r]
		fid = f.get("id")
		if not fid:
			return
		try:
			port_forward_manager.stop_forward(fid)
			f["status"] = "stopped"
			f.pop("id", None)
		except Exception as e:
			QMessageBox.warning(self, "Tunneling", f"Failed to stop: {e}")
		self._refresh_table()
		self._save_tunnels()

	def _load_tunnels(self):
		if not os.path.exists(self._config_file):
			return
		with open(self._config_file, 'r', encoding='utf-8') as f:
			data = json.load(f)
			if isinstance(data, list):
				self._forwards = []
				for item in data:
					try:
						self._forwards.append({
							"name": item.get("name", ""),
							"type": item.get("type", "Local"),
							"session_index": int(item.get("session_index", 0)),
							"bind_host": item.get("bind_host", "127.0.0.1"),
							"bind_port": int(item.get("bind_port", 0)),
							"target_host": item.get("target_host", ""),
							"target_port": int(item.get("target_port", 0)),
							"status": item.get("status", "stopped")
						})
					except Exception:
						pass
		self._refresh_table()

	def _save_tunnels(self):
		# Persist non-ephemeral fields; do not save ephemeral connection id
		payload = []
		for fwd in self._forwards:
			payload.append({
				"name": fwd.get("name", ""),
				"type": fwd.get("type", "Local"),
				"session_index": fwd.get("session_index", 0),
				"bind_host": fwd.get("bind_host", "127.0.0.1"),
				"bind_port": fwd.get("bind_port", 0),
				"target_host": fwd.get("target_host", ""),
				"target_port": fwd.get("target_port", 0),
				"status": fwd.get("status", "stopped")
			})
		try:
			with open(self._config_file, 'w', encoding='utf-8') as f:
				json.dump(payload, f, ensure_ascii=False, indent=2)
		except Exception:
			pass

	def _start_all(self):
		for r in range(len(self._forwards)):
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

	def _stop_all(self):
		for r in range(len(self._forwards)):
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