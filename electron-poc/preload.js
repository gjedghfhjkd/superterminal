import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('api', {
  sshConnect: (cfg) => ipcRenderer.invoke('ssh-connect', cfg),
  sshOpenPty: () => ipcRenderer.invoke('ssh-open-pty'),
  sshSend: (data) => ipcRenderer.send('ssh-send', data),
  sshOnData: (cb) => ipcRenderer.on('ssh-data', (_, d) => cb(d)),
  sshResize: (size) => ipcRenderer.send('ssh-resize', size),

  sftpConnect: (cfg) => ipcRenderer.invoke('sftp-connect', cfg),
  sftpList: (remotePath) => ipcRenderer.invoke('sftp-list', remotePath)
})

