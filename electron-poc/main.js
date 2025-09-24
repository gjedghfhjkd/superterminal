import { app, BrowserWindow, ipcMain } from 'electron'
import { readFile, writeFile, readdir, stat, rm as fsrm, mkdir as fsmkdir, rename as fsrename } from 'fs/promises'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { Client as SSHClient } from 'ssh2'
import SFTPClient from 'ssh2-sftp-client'
import net from 'net'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Configure portable userData directory next to the executable
try {
  const isDev = !app.isPackaged
  const baseDir = isDev ? __dirname : path.dirname(process.execPath)
  const dataDir = path.join(baseDir, 'data')
  try { fs.mkdirSync(dataDir, { recursive: true }) } catch {}
  app.setPath('userData', dataDir)
} catch {}

let win
let terminalHasFocus = false
function createWindow() {
  win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'SuperTerminal',
    icon: path.join(__dirname, 'assets', 'icon.svg'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })
  try { app.setName('SuperTerminal') } catch {}
  try { win.setTitle('SuperTerminal') } catch {}
  try {
    win.webContents.on('before-input-event', (event, input) => {
      try {
        const isCtrlW = (input && (input.control || input.meta) && String(input.key || '').toLowerCase() === 'w')
        // Block Ctrl/Cmd+W only when terminal is NOT focused (allow terminals to handle it)
        if (isCtrlW && !terminalHasFocus) { event.preventDefault() }
      } catch {}
    })
  } catch {}
  win.loadFile('renderer.html')
}
// Focus coordination from renderer
import { ipcMain as _ipcMain } from 'electron'
ipcMain.on('terminal-focus', (_e, focused) => {
  try { terminalHasFocus = !!focused } catch {}
})

app.whenReady().then(createWindow)

// Manage multiple connections
const connections = new Map() // id -> { ssh, sftp, stream }
// key `${id}:${localPort}` -> { server, sockets:Set<net.Socket>, streams:Set<ssh2.Stream> }
const forwards = new Map()

// Sessions persistence
const sessionsFile = () => path.join(app.getPath('userData'), 'sessions.json')
async function loadSessions() {
  try {
    const txt = await readFile(sessionsFile(), 'utf-8')
    const data = JSON.parse(txt)
    if (Array.isArray(data)) return data // legacy raw array
    if (data && Array.isArray(data.sessions)) return data.sessions // legacy v1
    if (data && Array.isArray(data.tree)) return data.tree // v2 tree
    return []
  } catch {
    return []
  }
}
async function saveSessionsTree(tree) {
  const payload = { version: 2, tree }
  await writeFile(sessionsFile(), JSON.stringify(payload, null, 2))
}

// Tunnels persistence
const tunnelsFile = () => path.join(app.getPath('userData'), 'tunnels.json')
async function loadTunnels() {
  try {
    const txt = await readFile(tunnelsFile(), 'utf-8')
    const data = JSON.parse(txt)
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data.tunnels)) return data.tunnels
    return []
  } catch { return [] }
}
async function saveTunnels(tunnels) {
  const payload = { version: 1, tunnels: Array.isArray(tunnels) ? tunnels : [] }
  await writeFile(tunnelsFile(), JSON.stringify(payload, null, 2))
}

// Users persistence
const usersFile = () => path.join(app.getPath('userData'), 'users.json')
async function loadUsers() {
  try {
    const txt = await readFile(usersFile(), 'utf-8')
    const data = JSON.parse(txt)
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data.users)) return data.users
    return []
  } catch { return [] }
}
async function saveUsers(users) {
  const payload = { version: 1, users: Array.isArray(users) ? users : [] }
  await writeFile(usersFile(), JSON.stringify(payload, null, 2))
}

ipcMain.handle('sessions-load', async () => {
  const data = await loadSessions()
  // normalize to { tree }
  let tree
  if (Array.isArray(data)) {
    const looksLikeTree = data.some(e => e && typeof e === 'object' && 'type' in e)
    tree = looksLikeTree ? data : data.map((s, i) => ({ id: String(i), type:'session', name: `${s.name||s.host||'Session'} (${s.username||'user'})`, session: s }))
  } else {
    tree = data
  }
  return { ok: true, tree }
})
ipcMain.handle('sessions-save', async (evt, tree) => {
  await saveSessionsTree(tree || [])
  try { win.webContents.send('sessions-updated') } catch {}
  return { ok: true }
})

// Tunnels load/save
ipcMain.handle('tunnels-load', async () => {
  const tunnels = await loadTunnels()
  return { ok: true, tunnels }
})
ipcMain.handle('tunnels-save', async (evt, tunnels) => {
  await saveTunnels(tunnels || [])
  try { win.webContents.send('tunnels-updated') } catch {}
  return { ok: true }
})
// Users load/save
ipcMain.handle('users-load', async () => {
  const users = await loadUsers()
  return { ok: true, users }
})
ipcMain.handle('users-save', async (evt, users) => {
  await saveUsers(users || [])
  try { win.webContents.send('users-updated') } catch {}
  return { ok: true }
})
// Open separate window to create/edit a user
ipcMain.handle('open-user-window', async (evt, payload) => {
  const preset = payload && payload.preset ? payload.preset : null
  return new Promise(async (resolve) => {
    const child = new BrowserWindow({
      width: 480,
      height: 520,
      parent: win,
      modal: true,
      autoHideMenuBar: true,
      webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.js') }
    })
    try { child.setMenu(null) } catch {}
    let resolved = false
    const handler = (_, user) => {
      if (resolved) return
      resolved = true
      try { child.close() } catch {}
      resolve({ ok: true, user })
    }
    ipcMain.once('user-form-submit', handler)
    const query = preset ? { preset: encodeURIComponent(JSON.stringify(preset)) } : {}
    await child.loadFile('user_form.html', { query })
    child.on('closed', () => { if (!resolved) resolve({ ok: false }) })
  })
})
// Open separate window to create/edit a tunnel
ipcMain.handle('open-tunnel-window', async (evt, payload) => {
  const preset = payload && payload.preset ? payload.preset : null
  return new Promise(async (resolve) => {
    const child = new BrowserWindow({
      width: 420,
      height: 520,
      parent: win,
      modal: true,
      autoHideMenuBar: true,
      webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.js') }
    })
    try { child.setMenu(null) } catch {}
    let resolved = false
    const handler = (_, tunnel) => {
      if (resolved) return
      resolved = true
      try { child.close() } catch {}
      resolve({ ok: true, tunnel })
    }
    ipcMain.once('tunnel-form-submit', handler)
    const query = preset ? { preset: encodeURIComponent(JSON.stringify(preset)) } : {}
    await child.loadFile('tunnel_form.html', { query })
    child.on('closed', () => { if (!resolved) resolve({ ok: false }) })
  })
})
// legacy handlers kept as no-ops to avoid errors if called
ipcMain.handle('sessions-add', async (evt, session) => {
  const existing = await loadSessions()
  const tree = Array.isArray(existing) ? existing.map((s, i) => ({ id:String(i), type:'session', name:`${s.username||'user'}@${s.host||'host'}:${s.port||22}`, session:s })) : existing
  tree.push({ id: String(Date.now()), type:'session', name: `${session.username||'user'}@${session.host||'host'}:${session.port||22}`, session })
  await saveSessionsTree(tree)
  try { win.webContents.send('sessions-updated') } catch {}
  return { ok: true }
})
ipcMain.handle('sessions-delete', async (evt, index) => {
  const data = await loadSessions()
  let tree = Array.isArray(data) ? data.map((s, i) => ({ id:String(i), type:'session', name:`${s.username||'user'}@${s.host||'host'}:${s.port||22}`, session:s })) : data
  if (index >= 0 && index < tree.length) tree.splice(index, 1)
  await saveSessionsTree(tree)
  try { win.webContents.send('sessions-updated') } catch {}
  return { ok: true }
})

ipcMain.handle('ssh-connect', async (evt, cfg) => {
  return new Promise((resolve, reject) => {
    const id = cfg.id
    const ssh = new SSHClient()
    ssh.on('ready', () => {
      try { console.log('[ssh-connect] ready', id) } catch {}
      let rec = connections.get(id) || {}
      rec.ssh = ssh
      connections.set(id, rec)
      resolve({ ok: true })
    })
    ssh.on('error', (e) => { try { console.error('[ssh-connect] error', e) } catch {}; reject(new Error(String(e))) })
    const conn = {
      host: cfg.host, port: cfg.port, username: cfg.username,
      readyTimeout: 10000
    }
    // Merge user preset if present (cfg.userPreset fields)
    try {
      const preset = cfg.userPreset && typeof cfg.userPreset === 'object' ? cfg.userPreset : null
      if (preset) {
        if (!conn.host && preset.host) conn.host = preset.host
        if (!conn.port && preset.port) conn.port = preset.port
        if (!conn.username && preset.username) conn.username = preset.username
        if (preset.auth && !cfg.auth) cfg.auth = preset.auth
        if (!cfg.password && preset.password) cfg.password = preset.password
        if (!cfg.privateKey && preset.privateKey) cfg.privateKey = preset.privateKey
        if (!cfg.passphrase && preset.passphrase) cfg.passphrase = preset.passphrase
      }
    } catch {}
    if (cfg.auth === 'password') {
      if (!cfg.password) return reject(new Error('Password is required'))
      conn.password = cfg.password
    } else {
      const key = (cfg.privateKey || '').trim()
      if (!key) return reject(new Error('Private key is required'))
      conn.privateKey = key
      if (cfg.passphrase) conn.passphrase = cfg.passphrase
    }
    try { console.log('[ssh-connect] connecting', { id, host: conn.host, port: conn.port, username: conn.username }) } catch {}
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
      try { stream.stderr && stream.stderr.on && stream.stderr.on('data', (d) => win.webContents.send('ssh-data', { id, data: d.toString('utf8') })) } catch {}
      resolve({ ok: true })
    })
  })
})

ipcMain.handle('sftp-connect', async (evt, cfg) => {
  const id = cfg.id
  const sftp = new SFTPClient()
  const options = { host: cfg.host, port: cfg.port, username: cfg.username }
  // Merge user preset if present
  try {
    const preset = cfg.userPreset && typeof cfg.userPreset === 'object' ? cfg.userPreset : null
    if (preset) {
      if (!options.host && preset.host) options.host = preset.host
      if (!options.port && preset.port) options.port = preset.port
      if (!options.username && preset.username) options.username = preset.username
      if (preset.auth && !cfg.auth) cfg.auth = preset.auth
      if (!cfg.password && preset.password) cfg.password = preset.password
      if (!cfg.privateKey && preset.privateKey) cfg.privateKey = preset.privateKey
      if (!cfg.passphrase && preset.passphrase) cfg.passphrase = preset.passphrase
    }
  } catch {}
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

// Local port forwarding via ssh2 (L->R)
ipcMain.handle('tunnel-start', async (evt, payload) => {
  const { id, localHost='127.0.0.1', localPort, remoteHost='127.0.0.1', remotePort } = payload || {}
  if (!id || !localPort || !remoteHost || !remotePort) throw new Error('Invalid tunnel params')
  const rec = connections.get(id)
  if (!rec || !rec.ssh) throw new Error('Not connected')
  const key = `${id}:${localPort}`
  if (forwards.has(key)) return { ok: true }
  const sockets = new Set()
  const streams = new Set()
  const server = net.createServer((socket) => {
    // Track sockets so we can destroy them on stop (e.g., HTTP keep-alive)
    sockets.add(socket)
    socket.on('close', () => { try { sockets.delete(socket) } catch {} })
    socket.on('error', () => {})
    rec.ssh.forwardOut(socket.remoteAddress || '127.0.0.1', socket.remotePort || 0, remoteHost, remotePort, (err, stream) => {
      if (err) { try { socket.destroy() } catch {}; return }
      // Track SSH streams to close them on stop
      try {
        streams.add(stream)
        stream.on('close', () => { try { streams.delete(stream) } catch {} })
        stream.on('error', () => {})
      } catch {}
      socket.pipe(stream).pipe(socket)
    })
  })
  await new Promise((resolve, reject) => {
    server.on('error', (e) => { try { console.error('[tunnel-start] server error', e) } catch {}; reject(e) })
    server.listen(localPort, localHost, resolve)
  })
  forwards.set(key, { server, sockets, streams })
  return { ok: true }
})

ipcMain.handle('tunnel-stop', async (evt, payload) => {
  const { id, localPort } = payload || {}
  const key = `${id}:${localPort}`
  const entry = forwards.get(key)
  if (entry) {
    try {
      // Force-close active TCP sockets and SSH streams to unblock server.close
      if (entry.sockets && typeof entry.sockets.forEach === 'function') {
        entry.sockets.forEach((s) => { try { s.destroy() } catch {} })
        try { entry.sockets.clear() } catch {}
      }
      if (entry.streams && typeof entry.streams.forEach === 'function') {
        entry.streams.forEach((st) => { try { st.end() } catch {}; try { st.destroy() } catch {} })
        try { entry.streams.clear() } catch {}
      }
    } catch {}
    try { await new Promise((r) => entry.server.close(r)) } catch {}
    forwards.delete(key)
  }
  return { ok: true }
})

ipcMain.handle('sftp-list', async (evt, remotePath) => {
  // optional: choose any connected sftp (simplify POC)
  let first = null
  for (const rec of connections.values()) { if (rec.sftp) { first = rec.sftp; break } }
  if (!first) throw new Error('No SFTP connection')
  const list = await first.list(remotePath)
  // Normalize: ensure basename-only names and stable types
  return list.map(e => {
    const raw = String(e.name || '')
    const normalized = raw.replace(/\\+/g, '/').split('/').filter(Boolean)
    const base = normalized.length ? normalized[normalized.length - 1] : raw
    const type = (e.type === 'd') ? 'd' : (e.type === 'l' ? 'd' : 'file')
    return { name: base, displayName: base, pathName: base, size: e.size, type }
  })
})

// Per-connection SFTP list
ipcMain.handle('sftp-list-id', async (evt, payload) => {
  const { id, path: remotePath } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  const list = await rec.sftp.list(remotePath)
  return list.map(e => {
    const raw = String(e.name || '')
    const normalized = raw.replace(/\\+/g, '/').split('/').filter(Boolean)
    const base = normalized.length ? normalized[normalized.length - 1] : raw
    const type = (e.type === 'd') ? 'd' : (e.type === 'l' ? 'd' : 'file')
    return { name: base, displayName: base, pathName: base, size: e.size, type }
  })
})

// SFTP file operations
ipcMain.handle('sftp-delete', async (evt, payload) => {
  const { id, path: remotePath, isDir, recursive=true } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  if (isDir) { await rec.sftp.rmdir(remotePath, recursive) } else { await rec.sftp.delete(remotePath) }
  return { ok: true }
})
ipcMain.handle('sftp-rename', async (evt, payload) => {
  const { id, from, to } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  await rec.sftp.rename(from, to)
  return { ok: true }
})
ipcMain.handle('sftp-mkdir', async (evt, payload) => {
  const { id, path: remotePath } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  await rec.sftp.mkdir(remotePath, true)
  return { ok: true }
})
ipcMain.handle('sftp-upload', async (evt, payload) => {
  const { id, local, remote } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  await rec.sftp.fastPut(local, remote)
  return { ok: true }
})
ipcMain.handle('sftp-download', async (evt, payload) => {
  const { id, remote, local } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  await rec.sftp.fastGet(remote, local)
  return { ok: true }
})
ipcMain.handle('sftp-upload-dir', async (evt, payload) => {
  const { id, localDir, remoteDir } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  if (!rec.sftp.uploadDir) throw new Error('uploadDir not supported in ssh2-sftp-client version')
  await rec.sftp.uploadDir(localDir, remoteDir)
  return { ok: true }
})
ipcMain.handle('sftp-download-dir', async (evt, payload) => {
  const { id, remoteDir, localDir } = payload || {}
  const rec = connections.get(id)
  if (!rec || !rec.sftp) throw new Error('No SFTP connection for id')
  if (!rec.sftp.downloadDir) throw new Error('downloadDir not supported in ssh2-sftp-client version')
  await rec.sftp.downloadDir(remoteDir, localDir)
  return { ok: true }
})

// Local FS operations
ipcMain.handle('local-delete', async (evt, payload) => {
  const { path: localPath, isDir, recursive=true } = payload || {}
  if (isDir) await fsrm(localPath, { recursive, force: true })
  else await fsrm(localPath, { force: true })
  return { ok: true }
})
ipcMain.handle('local-rename', async (evt, payload) => {
  const { from, to } = payload || {}
  await fsrename(from, to)
  return { ok: true }
})
ipcMain.handle('local-mkdir', async (evt, payload) => {
  const { path: localPath } = payload || {}
  await fsmkdir(localPath, { recursive: true })
  return { ok: true }
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
  // Ensure any tunnels tied to this connection id are stopped and cleaned up
  const keysToClose = []
  for (const [k] of forwards.entries()) { if (k.startsWith(`${id}:`)) keysToClose.push(k) }
  for (const k of keysToClose) {
    const entry = forwards.get(k)
    if (!entry) continue
    try {
      if (entry.sockets) { entry.sockets.forEach((s) => { try { s.destroy() } catch {} }); try { entry.sockets.clear() } catch {} }
      if (entry.streams) { entry.streams.forEach((st) => { try { st.end() } catch {}; try { st.destroy() } catch {} }); try { entry.streams.clear() } catch {} }
    } catch {}
    try { await new Promise((r) => entry.server.close(r)) } catch {}
    forwards.delete(k)
  }
  return { ok: true }
})

// Open separate window to create a session
ipcMain.handle('open-session-window', async (evt, payload) => {
  const type = payload && payload.type ? payload.type : 'SSH'
  const preset = payload && payload.preset ? payload.preset : null
  return new Promise(async (resolve) => {
    const child = new BrowserWindow({
      width: 480,
      height: 640,
      parent: win,
      modal: true,
      autoHideMenuBar: true,
      webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.js') }
    })
    try { child.setMenu(null) } catch {}
    let resolved = false
    const handler = (_, sess) => {
      if (resolved) return
      resolved = true
      try { child.close() } catch {}
      resolve({ ok: true, session: sess })
    }
    ipcMain.once('session-form-submit', handler)
    const query = preset ? { type, preset: encodeURIComponent(JSON.stringify(preset)) } : { type }
    await child.loadFile('session_form.html', { query })
    child.on('closed', () => { if (!resolved) resolve({ ok: false }) })
  })
})

// Local filesystem listing for SFTP split view (left column)
ipcMain.handle('local-list', async (evt, localPath) => {
  try {
    const dirPath = localPath && typeof localPath === 'string' && localPath.length ? localPath : '/'
    const entries = await readdir(dirPath, { withFileTypes: true })
    const mapped = await Promise.all(entries.map(async (ent) => {
      const name = ent.name
      let type = 'file'
      try {
        if (ent.isDirectory()) {
          type = 'd'
        } else if (ent.isSymbolicLink()) {
          // Treat Windows junctions/symlinks as non-navigable to avoid EPERM on legacy compatibility links
          const full = path.join(dirPath, name)
          let st = null
          try { st = await stat(full) } catch (e) { st = null }
          type = 'link'
          // If explicitly desired, we could attempt to navigate only when readable, but default to non-dir
        }
      } catch {}
      return { name, type }
    }))
    // Sort: directories first, then files, by name
    mapped.sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name) : a.type === 'd' ? -1 : 1))
    return mapped
  } catch (e) {
    throw new Error('Local list error: ' + String(e))
  }
})

ipcMain.handle('get-home', async () => {
  try { return app.getPath('home') } catch { return '/' }
})

// OS-aware path helpers for renderer (local FS only)
ipcMain.handle('path-join', async (evt, payload) => {
  try {
    const a = (payload && payload.a) || ''
    const b = (payload && payload.b) || ''
    return path.join(a, b)
  } catch (e) {
    return ''
  }
})
ipcMain.handle('path-dirname', async (evt, payload) => {
  try {
    const p = (payload && payload.p) || ''
    return path.dirname(p)
  } catch (e) {
    return ''
  }
})

ipcMain.handle('sftp-disconnect', async (evt, id) => {
  const rec = connections.get(id)
  if (rec) {
    try { rec.sftp?.end?.() || rec.sftp?.close?.() } catch {}
    rec.sftp = undefined
    connections.set(id, rec)
  }
  return { ok: true }
})
