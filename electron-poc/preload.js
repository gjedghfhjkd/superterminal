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
  sftpListById: (id, remotePath) => ipcRenderer.invoke('sftp-list-id', { id, path: remotePath }),
  sftpDelete: (id, remotePath, isDir) => ipcRenderer.invoke('sftp-delete', { id, path: remotePath, isDir }),
  sftpRename: (id, from, to) => ipcRenderer.invoke('sftp-rename', { id, from, to }),
  sftpMkdir: (id, remotePath) => ipcRenderer.invoke('sftp-mkdir', { id, path: remotePath }),
  sftpUpload: (id, local, remote) => ipcRenderer.invoke('sftp-upload', { id, local, remote }),
  sftpDownload: (id, remote, local) => ipcRenderer.invoke('sftp-download', { id, remote, local }),
  sftpUploadDir: (id, localDir, remoteDir) => ipcRenderer.invoke('sftp-upload-dir', { id, localDir, remoteDir }),
  sftpDownloadDir: (id, remoteDir, localDir) => ipcRenderer.invoke('sftp-download-dir', { id, remoteDir, localDir }),

  sessionsLoad: () => ipcRenderer.invoke('sessions-load'),
  sessionsAdd: (session) => ipcRenderer.invoke('sessions-add', session),
  sessionsDelete: (idx) => ipcRenderer.invoke('sessions-delete', idx),
  sessionsSaveTree: (tree) => ipcRenderer.invoke('sessions-save', tree),
  openSessionWindow: (type='SSH') => ipcRenderer.invoke('open-session-window', { type }),
  openSessionWindowPreset: (type='SSH', preset=null) => ipcRenderer.invoke('open-session-window', { type, preset }),
  onSessionsUpdated: (cb) => ipcRenderer.on('sessions-updated', cb),
  sessionFormSubmit: (sess) => ipcRenderer.send('session-form-submit', sess),

  // multi-connection aware helpers (optional)
  sshOpenPtyId: (id) => ipcRenderer.invoke('ssh-open-pty-id', { id }),
  sshSendId: (id, data) => ipcRenderer.send('ssh-send', { id, data }),
  sshResizeId: (id, cols, rows) => ipcRenderer.send('ssh-resize', { id, cols, rows })
  ,
  // Local FS + SFTP helpers
  localList: (localPath) => ipcRenderer.invoke('local-list', localPath),
  localDelete: (localPath, isDir) => ipcRenderer.invoke('local-delete', { path: localPath, isDir }),
  localRename: (from, to) => ipcRenderer.invoke('local-rename', { from, to }),
  localMkdir: (localPath) => ipcRenderer.invoke('local-mkdir', { path: localPath }),
  getHome: () => ipcRenderer.invoke('get-home'),
  sftpDisconnect: (id) => ipcRenderer.invoke('sftp-disconnect', id)
})

