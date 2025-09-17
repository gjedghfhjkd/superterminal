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

// Manage multiple connections
const connections = new Map() // id -> { ssh, sftp, stream }

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
    const id = cfg.id
    const ssh = new SSHClient()
    ssh.on('ready', () => {
      let rec = connections.get(id) || {}
      rec.ssh = ssh
      connections.set(id, rec)
      resolve({ ok: true })
    })
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
    const id = arguments[0]?.senderFrame?.routingId ? null : null // unused
    // Renderer will send id in next handler, so expose explicit open-pty-id
    reject(new Error('Use ssh-open-pty-id with {id}'))
  })
})

ipcMain.handle('ssh-open-pty-id', async (evt, payload) => {
  return new Promise((resolve, reject) => {
    const id = payload.id
    const rec = connections.get(id)
    if (!rec || !rec.ssh) return reject(new Error('Not connected'))
    rec.ssh.shell({ term: 'xterm-256color', cols: 160, rows: 40 }, (err, stream) => {
      if (err) return reject(new Error(String(err)))
      rec.stream = stream
      connections.set(id, rec)
      stream.on('data', (d) => win.webContents.send('ssh-data', { id, data: d.toString('utf8') }))
      stream.on('close', () => win.webContents.send('ssh-data', { id, data: '\r\n[PTY closed]\r\n' }))
      resolve({ ok: true })
    })
  })
})

ipcMain.handle('sftp-connect', async (evt, cfg) => {
  const id = cfg.id
  const sftp = new SFTPClient()
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
  let rec = connections.get(id) || {}
  rec.sftp = sftp
  connections.set(id, rec)
  return { ok: true }
})

ipcMain.handle('sftp-list', async (evt, remotePath) => {
  // optional: choose any connected sftp (simplify POC)
  let first = null
  for (const rec of connections.values()) { if (rec.sftp) { first = rec.sftp; break } }
  if (!first) throw new Error('No SFTP connection')
  const list = await first.list(remotePath)
  return list.map(e => ({ name: e.name, size: e.size, type: e.type }))
})

ipcMain.on('ssh-send', (e, payload) => {
  const { id, data } = payload
  const rec = connections.get(id)
  if (rec && rec.stream) {
    try { rec.stream.write(data) } catch {}
  }
})

ipcMain.on('ssh-resize', (e, payload) => {
  const { id, cols, rows } = payload
  const rec = connections.get(id)
  if (rec && rec.stream) {
    try { rec.stream.setWindow(rows, cols, 0, 0) } catch {}
  }
})

ipcMain.handle('ssh-disconnect', async (e, id) => {
  const rec = connections.get(id)
  if (rec) {
    try { rec.stream?.end() } catch {}
    try { rec.sftp?.end?.() || rec.sftp?.close?.() } catch {}
    try { rec.ssh?.end?.() } catch {}
    connections.delete(id)
  }
  return { ok: true }
})

// Open separate window to create a session
ipcMain.handle('open-session-window', async (evt, payload) => {
  const type = payload && payload.type ? payload.type : 'SSH'
  const child = new BrowserWindow({
    width: 480,
    height: 640,
    parent: win,
    modal: true,
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.js') }
  })
  try { child.setMenu(null) } catch {}
  await child.loadFile('session_form.html', { query: { type } })
  return { ok: true }
})
