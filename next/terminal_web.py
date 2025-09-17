from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebChannel import QWebChannel
except Exception:
    QWebEngineView = None
    QWebChannel = None

HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="https://unpkg.com/xterm@5.3.0/css/xterm.css" />
    <style>
      html, body { margin:0; height:100%; background:#0f111a; }
      #term { height:100%; width:100%; }
    </style>
  </head>
  <body>
    <div id="term"></div>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script src="https://unpkg.com/xterm@5.3.0/lib/xterm.js"></script>
    <script>
      const term = new Terminal({cursorBlink:true, theme:{background:'#0f111a', foreground:'#e6e6e6'}});
      term.open(document.getElementById('term'));
      new QWebChannel(qt.webChannelTransport, function(ch){
        const bridge = ch.objects.bridge;
        term.onData(data => bridge.onKey(data));
        bridge.writeText.connect(data => term.write(data));
      });
    </script>
  </body>
  </html>
"""

class Bridge(QObject):
    writeText = pyqtSignal(str)
    def __init__(self, sender_cb, parent=None):
        super().__init__(parent)
        self._send = sender_cb
    @pyqtSlot(str)
    def onKey(self, data: str):
        try:
            if self._send:
                self._send(data)
        except Exception:
            pass

class TerminalWeb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if QWebEngineView is None:
            raise RuntimeError('QtWebEngine not available')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.view = QWebEngineView(self)
        layout.addWidget(self.view)
        self.channel = QWebChannel(self.view.page())
        self._bridge = None
        self.view.page().setWebChannel(self.channel)
        self.view.setHtml(HTML)

    def set_sender(self, sender_callable):
        self._bridge = Bridge(sender_callable, self)
        self.channel.registerObject('bridge', self._bridge)

    def append_output(self, text: str):
        if self._bridge:
            self._bridge.writeText.emit(text)

