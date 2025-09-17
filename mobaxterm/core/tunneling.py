import socket
import threading
import time
import paramiko
from typing import Dict, Optional, Tuple, List
from ..models.session import Session

class PortForward:
	def __init__(self, kind: str, session_index: int, bind_host: str, bind_port: int,
				 target_host: str, target_port: int):
		self.kind = kind  # 'Local' or 'Remote'
		self.session_index = session_index
		self.bind_host = bind_host
		self.bind_port = bind_port
		self.target_host = target_host
		self.target_port = target_port
		self._stop_event = threading.Event()
		self._thread: Optional[threading.Thread] = None
		self._client: Optional[paramiko.SSHClient] = None
		self._transport: Optional[paramiko.Transport] = None
		self._listen_sock: Optional[socket.socket] = None  # for Local (-L)
		self._started_ok = False

	def stop(self):
		try:
			self._stop_event.set()
			# Cancel remote forward if needed
			if self.kind == 'Remote' and self._transport is not None:
				try:
					self._transport.cancel_port_forward(self.bind_host, self.bind_port)
				except Exception:
					pass
			# Close listening socket if any
			if self._listen_sock is not None:
				try:
					self._listen_sock.close()
				except Exception:
					pass
			# Close SSH client
			if self._client is not None:
				try:
					self._client.close()
				except Exception:
					pass
			# Join thread
			if self._thread and self._thread.is_alive():
				self._thread.join(timeout=2.0)
		except Exception:
			pass

class PortForwardManager:
	def __init__(self):
		self._forwards: Dict[str, PortForward] = {}
		self._lock = threading.Lock()
		# Session provider hook; set from UI to resolve sessions
		self._get_session = None  # type: Optional[callable]

	def set_session_resolver(self, resolver_callable):
		self._get_session = resolver_callable

	def list_forwards(self) -> List[Tuple[str, PortForward]]:
		with self._lock:
			return list(self._forwards.items())

	def stop_forward(self, forward_id: str) -> bool:
		with self._lock:
			pf = self._forwards.get(forward_id)
		if not pf:
			return False
		pf.stop()
		with self._lock:
			self._forwards.pop(forward_id, None)
		return True

	def _connect(self, session: Session) -> paramiko.SSHClient:
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		kwargs = {
			'hostname': session.host,
			'port': session.port,
			'username': session.username,
			'timeout': 10,
		}
		if getattr(session, 'auth_method', 'password') == 'key':
			kwargs['key_filename'] = getattr(session, 'private_key_path', None)
			kwargs['passphrase'] = getattr(session, 'private_key_passphrase', None)
			kwargs['allow_agent'] = True
			kwargs['look_for_keys'] = True
		else:
			kwargs['password'] = getattr(session, 'password', None)
			kwargs['allow_agent'] = False
			kwargs['look_for_keys'] = False
		client.connect(**kwargs)
		return client

	def _spawn(self, pf: PortForward, target):
		pf._thread = threading.Thread(target=target, args=(pf,))
		pf._thread.daemon = True
		pf._thread.start()

	def start_local_forward(self, session_index: int, bind_host: str, bind_port: int,
							target_host: str, target_port: int) -> str:
		pf = PortForward('Local', session_index, bind_host, bind_port, target_host, target_port)
		forward_id = f"L:{session_index}:{bind_host}:{bind_port}->{target_host}:{target_port}:{int(time.time()*1000)}"
		def _runner(p: PortForward):
			try:
				# connect SSH
				sess = self._get_session(p.session_index) if self._get_session else None
				if not sess:
					return
				p._client = self._connect(sess)
				p._transport = p._client.get_transport()
				# listen locally
				p._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				p._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				p._listen_sock.bind((p.bind_host, p.bind_port))
				p._listen_sock.listen(100)
				p._started_ok = True
				while not p._stop_event.is_set():
					p._listen_sock.settimeout(1.0)
					try:
						client_sock, addr = p._listen_sock.accept()
					except socket.timeout:
						continue
					# Open direct-tcpip channel to target via SSH
					try:
						chan = p._transport.open_channel('direct-tcpip', (p.target_host, p.target_port), addr)
					except Exception:
						client_sock.close()
						continue
					self._bridge(chan, client_sock)
				# cleanup
			except Exception:
				pass
			finally:
				p.stop()
		self._register(forward_id, pf)
		self._spawn(pf, _runner)
		# Wait briefly to confirm started
		self._wait_started(pf)
		return forward_id

	def start_remote_forward(self, session_index: int, bind_host: str, bind_port: int,
							target_host: str, target_port: int) -> str:
		pf = PortForward('Remote', session_index, bind_host, bind_port, target_host, target_port)
		forward_id = f"R:{session_index}:{bind_host}:{bind_port}->{target_host}:{target_port}:{int(time.time()*1000)}"
		def _runner(p: PortForward):
			try:
				# connect SSH
				sess = self._get_session(p.session_index) if self._get_session else None
				if not sess:
					return
				p._client = self._connect(sess)
				p._transport = p._client.get_transport()
				# Request remote port forward
				p._transport.request_port_forward(p.bind_host, p.bind_port)
				p._started_ok = True
				while not p._stop_event.is_set():
					chan = p._transport.accept(1.0)
					if chan is None:
						continue
					# For each remote incoming connection, bridge to local TCP target
					try:
						local_sock = socket.create_connection((p.target_host, p.target_port), timeout=10)
					except Exception:
						try:
							chan.close()
						except Exception:
							pass
						continue
					self._bridge(chan, local_sock)
				# cleanup
			except Exception:
				pass
			finally:
				p.stop()
		self._register(forward_id, pf)
		self._spawn(pf, _runner)
		self._wait_started(pf)
		return forward_id

	def _bridge(self, chan, sock):
		# Bidirectional copy between Paramiko Channel and socket
		def _copy(src, dst, is_channel_to_sock: bool):
			try:
				while True:
					data = src.recv(32768) if is_channel_to_sock else src.recv(32768)
					if not data:
						break
					dst.sendall(data)
			except Exception:
				pass
		try:
			thr1 = threading.Thread(target=_copy, args=(chan, sock, True), daemon=True)
			thr2 = threading.Thread(target=_copy, args=(sock, chan, False), daemon=True)
			thr1.start(); thr2.start()
			thr1.join(); thr2.join()
		finally:
			try:
				sock.close()
			except Exception:
				pass
			try:
				chan.close()
			except Exception:
				pass

	def _register(self, forward_id: str, pf: PortForward):
		with self._lock:
			self._forwards[forward_id] = pf

	def _wait_started(self, pf: PortForward, timeout: float = 2.0):
		start = time.time()
		while time.time() - start < timeout:
			if pf._started_ok:
				return
			time.sleep(0.05)

# Singleton manager
port_forward_manager = PortForwardManager()