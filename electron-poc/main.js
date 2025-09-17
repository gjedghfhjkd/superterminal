import { app, BrowserWindow, ipcMain } from 'electron'
import { readFile, writeFile } from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { Client as SSHClient } from 'ssh2'
import SFTPClient from 'ssh2-sftp-client'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let win
function createWindow() {
  win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })
  win.loadFile('renderer.html')
}

app.whenReady().then(createWindow)

let ssh = null
let sftp = null

// Sessions persistence
const sessionsFile = () => path.join(app.getPath('userData'), 'sessions.json')
async function loadSessions() {
  try {
    const txt = await readFile(sessionsFile(), 'utf-8')
    const data = JSON.parse(txt)
    if (Array.isArray(data)) return data
    return data && Array.isArray(data.sessions) ? data.sessions : []
  } catch {
    return []
  }
}
async function saveSessions(sessions) {
  const payload = { version: 1, sessions }
  await writeFile(sessionsFile(), JSON.stringify(payload, null, 2))
}

ipcMain.handle('sessions-load', async () => {
  const sessions = await loadSessions()
  return { ok: true, sessions }
})
ipcMain.handle('sessions-add', async (evt, session) => {
  const sessions = await loadSessions()
  sessions.push(session)
  await saveSessions(sessions)
  return { ok: true, sessions }
})
ipcMain.handle('sessions-delete', async (evt, index) => {
  const sessions = await loadSessions()
  if (index >= 0 && index < sessions.length) sessions.splice(index, 1)
  await saveSessions(sessions)
  return { ok: true, sessions }
})

ipcMain.handle('ssh-connect', async (evt, cfg) => {
  return new Promise((resolve, reject) => {
    ssh = new SSHClient()
    ssh.on('ready', () => resolve({ ok: true }))
    ssh.on('error', (e) => reject(new Error(String(e))))
    const conn = {
      host: cfg.host, port: cfg.port, username: cfg.username,
      readyTimeout: 10000
    }
    if (cfg.auth === 'password') {
      if (!cfg.password) return reject(new Error('Password is required'))
      conn.password = cfg.password
    } else {
      const key = (cfg.privateKey || '').trim()
      if (!key) return reject(new Error('Private key is required'))
      conn.privateKey = key
      if (cfg.passphrase) conn.passphrase = cfg.passphrase
    }
    ssh.connect(conn)
  })
})

ipcMain.handle('ssh-open-pty', async () => {
  return new Promise((resolve, reject) => {
    if (!ssh) return reject('Not connected')
    ssh.shell({ term: 'xterm-256color', cols: 160, rows: 40 }, (err, stream) => {
      if (err) return reject(String(err))
      stream.on('data', (d) => win.webContents.send('ssh-data', d.toString('utf8')))
      stream.on('close', () => win.webContents.send('ssh-data', '\r\n[PTY closed]\r\n'))
      ipcMain.on('ssh-send', (e, data) => stream.write(data))
      ipcMain.on('ssh-resize', (e, size) => stream.setWindow(size.rows, size.cols, 0, 0))
      resolve({ ok: true })
    })
  })
})

ipcMain.handle('sftp-connect', async (evt, cfg) => {
  sftp = new SFTPClient()
  const options = { host: cfg.host, port: cfg.port, username: cfg.username }
  if (cfg.auth === 'password') {
    if (!cfg.password) throw new Error('Password is required')
    options.password = cfg.password
  } else {
    const key = (cfg.privateKey || '').trim()
    if (!key) throw new Error('Private key is required')
    options.privateKey = key
    if (cfg.passphrase) options.passphrase = cfg.passphrase
  }
  await sftp.connect(options)
  return { ok: true }
})

ipcMain.handle('sftp-list', async (evt, remotePath) => {
  const list = await sftp.list(remotePath)
  return list.map(e => ({ name: e.name, size: e.size, type: e.type }))
})
