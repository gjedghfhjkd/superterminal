from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebChannel import QWebChannel
except Exception:
    QWebEngineView = None
    QWebChannel = None

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/xterm@5.3.0/css/xterm.css" />
  <style>
    html, body { height:100%; width:100%; margin:0; background:#0f111a; }
    #term { height:100%; width:100%; }
  </style>
</head>
<body>
  <div id="term"></div>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <script src="https://unpkg.com/xterm@5.3.0/lib/xterm.js"></script>
  <script>
    const term = new Terminal({
      convertEol: false,
      cursorBlink: true,
      theme: {
        background: '#0f111a',
        foreground: '#e6e6e6'
      }
    });
    term.open(document.getElementById('term'));
    new QWebChannel(qt.webChannelTransport, function(channel){
      window.bridge = channel.objects.bridge;
      term.onData(function(data){
        bridge.onKey(data);
      });
      bridge.writeText.connect(function(data){
        term.write(data);
      });
    });
    window.addEventListener('resize', function(){
      // xterm.js can fit with addon; for simplicity we rely on CSS stretch here
    });
  </script>
</body>
<html>
"""

class Bridge(QObject):
    writeText = pyqtSignal(str)
    def __init__(self, sender_cb, parent=None):
        super().__init__(parent)
        self._sender = sender_cb
    @pyqtSlot(str)
    def onKey(self, data: str):
        try:
            if self._sender:
                self._sender(data)
        except Exception:
            pass

class TerminalJS(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        if QWebEngineView is None:
            raise RuntimeError("QtWebEngine is not available")
        self.view = QWebEngineView(self)
        layout.addWidget(self.view)
        self.channel = QWebChannel(self.view.page())
        # Bridge will be set after set_sender
        self._bridge = None
        self.view.page().setWebChannel(self.channel)
        self.view.setHtml(HTML)

    def set_sender(self, sender_callable):
        try:
            self._bridge = Bridge(sender_callable, self)
            self.channel.registerObject('bridge', self._bridge)
        except Exception:
            pass

    # compatibility for SSH thread
    def append_output(self, text: str):
        try:
            if self._bridge:
                # Emit via signal to JS
                self._bridge.writeText.emit(text)
        except Exception:
            pass

