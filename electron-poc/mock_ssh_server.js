import ssh2Pkg from 'ssh2'
const { Server } = ssh2Pkg
import os from 'os'
import process from 'process'
import { spawn } from 'child_process'
// Try to load a PTY implementation: prefer node-pty; otherwise null
const PTY_PROMISE = (async () => {
  try { const m = await import('node-pty'); return m.default || m } catch {}
  return null
})()
import { generateKeyPairSync } from 'crypto'

const HOST = process.env.MOCK_SSH_HOST || '127.0.0.1'
const PORT = Number(process.env.MOCK_SSH_PORT || 2222)

// Generate an in-memory RSA host key so no files are needed
const { privateKey: hostKeyPem } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
  publicKeyEncoding: { type: 'pkcs1', format: 'pem' },
  privateKeyEncoding: { type: 'pkcs1', format: 'pem' }
})

function start() {
  const server = new Server({ hostKeys: [hostKeyPem] }, (client) => {
    console.log('[mock-ssh] client connected')

    client.on('error', (e) => console.error('[mock-ssh] client error:', e?.message || e))

    client.on('authentication', (ctx) => {
      // Accept simple creds for testing
      if (ctx.method === 'password') {
        // Any username, password must be 'test'
        if (String(ctx.password) === 'test') return ctx.accept()
        return ctx.reject()
      }
      if (ctx.method === 'publickey') {
        // Accept any public key for local testing
        return ctx.accept()
      }
      // Fallback: reject others
      return ctx.reject()
    })

    client.on('ready', () => {
      console.log('[mock-ssh] client authenticated')

      client.on('session', (accept) => {
        const session = accept()

        const termInfo = { cols: 80, rows: 24 }
        let ptyProcess = null

        session.on('pty', (accept, reject, info) => {
          try {
            termInfo.cols = info && info.cols ? info.cols : 80
            termInfo.rows = info && info.rows ? info.rows : 24
          } catch {}
          try { accept && accept() } catch {}
        })

        session.on('window-change', (accept, _reject, info) => {
          try {
            termInfo.cols = info && info.cols ? info.cols : termInfo.cols
            termInfo.rows = info && info.rows ? info.rows : termInfo.rows
            if (ptyProcess && typeof ptyProcess.resize === 'function') {
              ptyProcess.resize(termInfo.cols, termInfo.rows)
            }
          } catch {}
          try { accept && accept() } catch {}
        })

        session.on('shell', async (accept) => {
          const stream = accept()
          // Idle timeout (5s) to simulate disconnects for reconnect testing
          const IDLE_MS = 5000
          let idleTimer = null
          const resetIdle = () => {
            try { clearTimeout(idleTimer) } catch {}
            idleTimer = setTimeout(() => {
              try { stream.write('\r\n[mock-ssh] idle timeout]\r\n') } catch {}
              try { stream.exit(0) } catch {}
              try { stream.end() } catch {}
            }, IDLE_MS)
          }
          const clearIdle = () => { try { clearTimeout(idleTimer) } catch {} }
          resetIdle()

          // Choose a shell (prefer bash), cross-platform
          const isWin = process.platform === 'win32'
          const shellCandidates = isWin
            ? [
                process.env.BASH || 'bash',
                'C:/Program Files/Git/bin/bash.exe',
                'C:/Program Files (x86)/Git/bin/bash.exe',
                'powershell.exe',
                process.env.COMSPEC || 'cmd.exe'
              ]
            : [process.env.SHELL || 'bash', 'bash', '/bin/bash', '/usr/bin/bash', '/bin/sh']

          const spawnArgsFor = (exe) => {
            const lower = String(exe).toLowerCase()
            if (isWin) {
              if (lower.includes('powershell')) return ['-NoLogo']
              if (lower.endsWith('cmd.exe') || lower === 'cmd') return []
              return ['-l']
            } else {
              if (lower.includes('bash') || lower.endsWith('/sh')) return ['-l']
              return ['-l']
            }
          }

          // Spawn a real PTY shell
          const pty = await PTY_PROMISE
          if (pty && typeof pty.spawn === 'function') {
            for (const exe of shellCandidates) {
              try {
                ptyProcess = pty.spawn(exe, spawnArgsFor(exe), {
                  name: 'xterm-256color',
                  cols: termInfo.cols,
                  rows: termInfo.rows,
                  cwd: process.cwd(),
                  env: { ...process.env, TERM: 'xterm-256color' }
                })
                ptyProcess.onData((d) => { try { stream.write(d) } catch {}; resetIdle() })
                stream.on('data', (d) => { try { ptyProcess.write(d.toString('utf8')) } catch {}; resetIdle() })
                stream.on('close', () => { clearIdle(); try { ptyProcess.kill() } catch {}; try { client.end() } catch {} })
                return
              } catch (e) {
                // try next candidate
              }
            }
          }

          // Fallback: spawn shell without PTY (reduced TTY features)
          // Line-by-line REPL fallback (works reliably without PTY)
          try { stream.write('\r\n[mock-ssh] No PTY available. Running simple shell (commands executed per line).\r\n') } catch {}
          const prompt = () => { try { stream.write('$ ') } catch {} }
          let buf = ''
          const runCommand = (line) => {
            const trimmed = (line || '').trim()
            if (!trimmed) { prompt(); return }
            const lower = trimmed.toLowerCase()
            if (lower === 'exit' || lower === 'logout' || lower === 'quit') { try { stream.exit(0) } catch {}; try { stream.end() } catch {}; return }
            let exe, args
            if (isWin) {
              exe = process.env.COMSPEC || 'cmd.exe'
              args = ['/d', '/s', '/c', trimmed]
            } else {
              exe = process.env.SHELL || '/bin/sh'
              args = ['-lc', trimmed]
            }
            try {
              const child = spawn(exe, args, { cwd: process.cwd(), env: { ...process.env } })
              child.stdout.on('data', (d) => { try { stream.write(d) } catch {}; resetIdle() })
              child.stderr.on('data', (d) => { try { stream.write(d) } catch {}; resetIdle() })
              child.on('close', (code) => {
                try { stream.write(`\r\n[exit ${code ?? 0}]\r\n`) } catch {}
                prompt()
                resetIdle()
              })
              child.on('error', (e) => {
                try { stream.write(`\r\n[error] ${String(e?.message||e)}\r\n`) } catch {}
                prompt()
                resetIdle()
              })
            } catch (e) {
              try { stream.write(`\r\n[error] ${String(e?.message||e)}\r\n`) } catch {}
              prompt()
              resetIdle()
            }
          }
          stream.on('data', (d) => {
            const s = d.toString('utf8')
            for (let i = 0; i < s.length; i++) {
              const ch = s[i]
              if (ch === '\r' || ch === '\n') {
                const line = buf
                buf = ''
                try { stream.write('\r\n') } catch {}
                runCommand(line)
                // collapse CRLF
                if (ch === '\r' && s[i+1] === '\n') i++
              } else if (ch === '\u0003') { // Ctrl+C
                buf = ''
                try { stream.write('^C\r\n') } catch {}
                prompt()
              } else if (ch === '\u0004') { // Ctrl+D (EOT)
                try { stream.write('^D\r\n') } catch {}
                try { stream.exit(0) } catch {}
                try { stream.end() } catch {}
              } else if (ch === '\u0008' || ch === '\u007f') { // Backspace/DEL
                if (buf.length) { buf = buf.slice(0, -1) }
                // Erase last char visually
                try { stream.write('\b \b') } catch {}
              } else if (ch >= ' ' && ch <= '~') {
                buf += ch
                // Local echo
                try { stream.write(ch) } catch {}
              }
            }
            resetIdle()
          })
          stream.on('close', () => { clearIdle(); try { client.end() } catch {} })
          prompt()
        })
      })

      // Optional: allow no-op exec requests
      client.on('exec', (accept, _reject, info) => {
        const stream = accept()
        stream.write(`Executed: ${info.command}\r\n`)
        try { stream.exit(0) } catch {}
        stream.end()
      })
    })

    client.on('end', () => console.log('[mock-ssh] client disconnected'))
  })

  server.on('error', (e) => {
    console.error('[mock-ssh] server error:', e?.message || e)
  })

  server.listen(PORT, HOST, () => {
    console.log(`[mock-ssh] listening on ${HOST}:${PORT}`)
    console.log('[mock-ssh] login with any username and password "test"')
  })
}

start()


