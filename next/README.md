# Web Terminal (xterm.js) + SSH/SFTP

This folder contains a fresh implementation of a terminal UI using xterm.js via QtWebEngine and a Python backend for SSH (PTY) and SFTP operations.

Structure:
- terminal_web.py: Qt widget embedding xterm.js with a WebChannel bridge
- ssh_backend.py: SSH client for PTY streaming
- sftp_backend.py: SFTP client skeleton
- demo_app.py: Minimal window to demo SSH terminal and SFTP panel