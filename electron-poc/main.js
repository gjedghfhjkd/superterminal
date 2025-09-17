import { app, BrowserWindow, ipcMain } from 'electron'
import { readFile } from 'fs/promises'
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
      preload: path.join(__dirname, 'preload.js')
    }
  })
  win.loadFile('renderer.html')
}

app.whenReady().then(createWindow)

let ssh = null
let sftp = null

ipcMain.handle('ssh-connect', async (evt, cfg) => {
  return new Promise((resolve, reject) => {
    ssh = new SSHClient()
    ssh.on('ready', () => resolve({ ok: true }))
    ssh.on('error', (e) => reject(String(e)))
    const conn = {
      host: cfg.host, port: cfg.port, username: cfg.username,
      readyTimeout: 10000
    }
    if (cfg.auth === 'password') conn.password = cfg.password
    else { conn.privateKey = cfg.privateKey; if (cfg.passphrase) conn.passphrase = cfg.passphrase }
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
  if (cfg.auth === 'password') options.password = cfg.password
  else { options.privateKey = cfg.privateKey; if (cfg.passphrase) options.passphrase = cfg.passphrase }
  await sftp.connect(options)
  return { ok: true }
})

ipcMain.handle('sftp-list', async (evt, remotePath) => {
  const list = await sftp.list(remotePath)
  return list.map(e => ({ name: e.name, size: e.size, type: e.type }))
})
