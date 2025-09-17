const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  sshConnect: (cfg) => ipcRenderer.invoke('ssh-connect', cfg),
  sshOpenPty: () => ipcRenderer.invoke('ssh-open-pty'),
  sshSend: (data) => ipcRenderer.send('ssh-send', data),
  sshOnData: (cb) => ipcRenderer.on('ssh-data', (_, d) => cb(d)),
  sshResize: (size) => ipcRenderer.send('ssh-resize', size),
  sshDisconnect: (id) => ipcRenderer.invoke('ssh-disconnect', id),

  sftpConnect: (cfg) => ipcRenderer.invoke('sftp-connect', cfg),
  sftpList: (remotePath) => ipcRenderer.invoke('sftp-list', remotePath),

  sessionsLoad: () => ipcRenderer.invoke('sessions-load'),
  sessionsAdd: (session) => ipcRenderer.invoke('sessions-add', session),
  sessionsDelete: (idx) => ipcRenderer.invoke('sessions-delete', idx),
  openSessionWindow: (type='SSH') => ipcRenderer.invoke('open-session-window', { type }),
  onSessionsUpdated: (cb) => ipcRenderer.on('sessions-updated', cb),

  // multi-connection aware helpers (optional)
  sshOpenPtyId: (id) => ipcRenderer.invoke('ssh-open-pty-id', { id }),
  sshSendId: (id, data) => ipcRenderer.send('ssh-send', { id, data }),
  sshResizeId: (id, cols, rows) => ipcRenderer.send('ssh-resize', { id, cols, rows })
})

