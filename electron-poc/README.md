SuperTerminal: Electron + xterm.js + ssh2 / ssh2-sftp-client

Setup:
1) cd electron-poc
2) npm install
3) npm start

Features:
- SSH PTY streaming to xterm.js (full-screen TUI compatible)
- SFTP basic listing
- Auth: password or pasted private key + passphrase

Comparison criteria to evaluate vs current PyQt terminals:
- Compatibility: vim/nano/top/htop/less; alt-screen behavior; mouse support (optional)
- Performance: input latency, screen redraw under load
- Stability: reconnection handling, error feedback
- Packaging: app size, dependencies, install complexity
