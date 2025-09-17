from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTextEdit, 
                             QHBoxLayout, QLineEdit, QLabel, QPushButton, QTabBar, QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QTextCursor, QKeySequence
from .custom_tab_widget import CloseButton
try:
    import pyte
except Exception:
    pyte = None
import re

class TerminalTab(QWidget):
    command_submitted = pyqtSignal(str)
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._send_key = None  # callable that sends raw data to SSH
        self._send_queue = []  # buffer keys until sender is ready
        self.initUI()
        # Track relative zoom steps applied to the terminal_output
        self._zoom_steps = 0
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Terminal output (now also used for input)
        self.terminal_output = QTextEdit()
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: #00ff00;
                border: none;
                padding: 5px;
            }
        """)
        # Set default monospace font via QFont so we can control zoom reliably
        default_font = QFont('Consolas')
        default_font.setStyleHint(QFont.Monospace)
        default_font.setFixedPitch(True)
        # Use a slightly smaller initial font for SSH sessions
        try:
            base_point_size = 12 if getattr(self.session, 'type', None) == 'SSH' else 14
        except Exception:
            base_point_size = 14
        default_font.setPointSize(base_point_size)
        self.terminal_output.setFont(default_font)
        self.terminal_output.document().setDefaultFont(default_font)
        self._default_font = QFont(self.terminal_output.font())
        self._base_point_size = self._default_font.pointSize()
        self.terminal_output.setPlainText("")
        # Disable line wrap to keep rows aligned with emulator screen
        self.terminal_output.setLineWrapMode(QTextEdit.NoWrap)
        self.terminal_output.installEventFilter(self)
        # Some key events are delivered to the viewport; filter there too
        self.terminal_output.viewport().installEventFilter(self)
        self.terminal_output.setCursorWidth(2)
        self.terminal_output.setFocusPolicy(Qt.StrongFocus)
        try:
            # Keep Tab inside the widget, not as focus-change
            self.terminal_output.setTabChangesFocus(False)
        except Exception:
            pass
        self.terminal_output.setReadOnly(True)
        
        # State for inline input handling
        self.input_enabled = False
        self.current_input = ""
        self.prompt_text = "$ "
        # Local echo is off by default; remote shell echoes characters
        self.local_echo_enabled = False
        # Minimal line editor state (fallback only)
        self._line_buffer = ""
        self._line_cursor = 0
        self._in_prompt = True

        # pyte screen/stream if available
        self._pyte_screen = None
        self._pyte_stream = None
        if pyte is not None:
            # Create a generous screen; resize is TODO
            self._pyte_screen = pyte.Screen(160, 40)
            self._pyte_stream = pyte.Stream(self._pyte_screen)
        # One-time cleanup right after first connect render
        self._first_connect_cleanup = True
        
        # Only the terminal area is shown; input happens inline
        layout.addWidget(self.terminal_output)
        
        # Shortcuts for zoom controls: Ctrl++, Ctrl+-, Ctrl+= (reset)
        try:
            # Standard platform zoom shortcuts
            sc_in_std = QShortcut(QKeySequence.ZoomIn, self)
            sc_in_std.setContext(Qt.WidgetWithChildrenShortcut)
            sc_in_std.activated.connect(self._apply_zoom_in)
            sc_out_std = QShortcut(QKeySequence.ZoomOut, self)
            sc_out_std.setContext(Qt.WidgetWithChildrenShortcut)
            sc_out_std.activated.connect(self._apply_zoom_out)
            for seq in ("Ctrl++", "Ctrl+Plus"):
                sc = QShortcut(QKeySequence(seq), self)
                sc.setContext(Qt.WidgetWithChildrenShortcut)
                sc.activated.connect(self._apply_zoom_in)
            for seq in ("Ctrl+-", "Ctrl+Minus"):
                sc = QShortcut(QKeySequence(seq), self)
                sc.setContext(Qt.WidgetWithChildrenShortcut)
                sc.activated.connect(self._apply_zoom_out)
            for seq in ("Ctrl+=", "Ctrl+Equal", "Ctrl+0"):
                sc = QShortcut(QKeySequence(seq), self)
                sc.setContext(Qt.WidgetWithChildrenShortcut)
                sc.activated.connect(self._apply_zoom_reset)
        except Exception:
            pass
        
    def enable_input(self):
        self.input_enabled = True
        # Make editable so caret blinks; eventFilter prevents local edits
        self.terminal_output.setReadOnly(False)
        self.terminal_output.setFocus()
        self.current_input = ""
        
    def disable_input(self):
        self.input_enabled = False
        self.terminal_output.setReadOnly(True)
        
    def append_output(self, text):
        # Preferred path: use pyte when available for correct terminal emulation
        if self._pyte_stream is not None:
            try:
                self._pyte_stream.feed(text)
                # Render entire screen to the QTextEdit
                # Ensure number of lines equals screen height for consistent positioning
                lines = list(self._pyte_screen.display)
                height = getattr(self._pyte_screen, 'lines', len(lines))
                if len(lines) < height:
                    lines += [""] * (height - len(lines))
                content = "\n".join(lines)
                # Cleanup tail: collapse excessive blank lines and duplicate prompts
                try:
                    def _cleanup_tail(text: str) -> str:
                        tail_lines = text.split('\n')
                        # Collapse trailing blanks to at most one
                        while len(tail_lines) >= 3 and tail_lines[-1].strip() == '' and tail_lines[-2].strip() == '':
                            tail_lines.pop()
                        # Deduplicate identical prompt lines at the very end
                        prompt_re = re.compile(r"(^.+@.+:.*[#$]\s*$|^\[[^\n]*\][#$]\s*$)")
                        # Keep removing duplicates among last lines
                        changed = True
                        while changed and len(tail_lines) >= 2:
                            changed = False
                            if prompt_re.search(tail_lines[-1]) and tail_lines[-1] == tail_lines[-2]:
                                tail_lines.pop(-2)
                                changed = True
                        return '\n'.join(tail_lines)
                    content = _cleanup_tail(content)
                except Exception:
                    pass
                self._first_connect_cleanup = False
                self.terminal_output.setPlainText(content)
                # Compute caret by moving cursor to row/col (0-based)
                row0 = max(0, min(self._pyte_screen.cursor.y, len(lines) - 1))
                line_text = lines[row0] if 0 <= row0 < len(lines) else ""
                col0 = max(0, min(self._pyte_screen.cursor.x, len(line_text)))
                cursor = self.terminal_output.textCursor()
                cursor.movePosition(QTextCursor.Start)
                # Move to the correct row (0-based)
                for _ in range(row0):
                    cursor.movePosition(QTextCursor.Down)
                cursor.movePosition(QTextCursor.StartOfLine)
                for _ in range(col0):
                    cursor.movePosition(QTextCursor.Right)
                self.terminal_output.setTextCursor(cursor)
                return
            except Exception:
                # Fallback to minimal logic below
                pass

        # Fallback: minimal parser for line editing sequences
        i = 0
        while i < len(text):
            ch = text[i]
            # Handle ESC sequences
            if ch == '\x1b':
                if i + 1 < len(text):
                    nxt = text[i + 1]
                    # OSC: ESC ] ... (BEL or ESC \) — skip
                    if nxt == ']':
                        i += 2
                        while i < len(text) and text[i] not in ('\x07',):
                            # handle ESC \
                            if text[i] == '\x1b' and i + 1 < len(text) and text[i+1] == '\\':
                                i += 2
                                break
                            i += 1
                        # skip terminator
                        i += 1
                        continue
                    # CSI: ESC [ ...
                    if nxt == '[':
                        i += 2
                        # collect parameters
                        params = ''
                        while i < len(text) and not ('@' <= text[i] <= '~'):
                            params += text[i]
                            i += 1
                        if i < len(text):
                            cmd = text[i]
                            # Handle a few basics
                            if cmd == 'D':  # cursor left
                                self._line_cursor = max(0, self._line_cursor - 1)
                                self._render_current_line()
                            elif cmd == 'C':  # cursor right
                                self._line_cursor = min(len(self._line_buffer), self._line_cursor + 1)
                                self._render_current_line()
                            elif cmd == 'G':  # CHA – cursor horizontal absolute
                                try:
                                    col = int(params) if params.isdigit() else 1
                                except Exception:
                                    col = 1
                                self._line_cursor = max(0, min(len(self._line_buffer), col - 1))
                                self._render_current_line()
                            elif cmd == 'K':  # erase in line (default: to end)
                                # Default to end-of-line when params empty
                                mode = params if params else '0'
                                if mode == '0':
                                    self._line_buffer = self._line_buffer[:self._line_cursor]
                                elif mode == '1':
                                    self._line_buffer = self._line_buffer[self._line_cursor:]
                                    self._line_cursor = 0
                                elif mode == '2':
                                    self._line_buffer = ''
                                    self._line_cursor = 0
                                self._render_current_line()
                            # ignore others
                            i += 1
                            continue
                # Unrecognized ESC, skip
                i += 1
                continue
            # BEL - ignore
            if ch == '\x07':
                i += 1
                continue
            # Backspace moves caret left
            if ch == '\x08':
                if self._line_cursor > 0:
                    self._line_cursor -= 1
                    self._render_current_line()
                i += 1
                continue
            # DEL treated like backspace erase
            if ch == '\x7f':
                if self._line_cursor > 0:
                    self._line_buffer = self._line_buffer[:self._line_cursor-1] + self._line_buffer[self._line_cursor:]
                    self._line_cursor -= 1
                    self._render_current_line()
                i += 1
                continue
            # CR / LF handling
            if ch == '\r':
                # Move to line start
                self._line_cursor = 0
                self._render_current_line()
                i += 1
                continue
            if ch == '\n':
                # Flush current line and newline
                self._replace_current_line(self._line_buffer)
                self._write('\n')
                self._line_buffer = ''
                self._line_cursor = 0
                self._in_prompt = True
                i += 1
                continue
            # Printable character
            # Detect beginning of input after prompt paint
            if self._in_prompt and ch not in (' ', '\t'):
                self._in_prompt = False
            self._line_buffer = (
                self._line_buffer[:self._line_cursor] + ch + self._line_buffer[self._line_cursor:]
            )
            self._line_cursor += 1
            self._render_current_line()
            i += 1
        # Auto-scroll to bottom only when a newline is printed; otherwise
        # keep caret where server editing logic placed it
        if '\n' in text:
            cursor = self.terminal_output.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.terminal_output.setTextCursor(cursor)
            # Aggressively collapse trailing empty lines to a single one
            try:
                doc = self.terminal_output.document()
                # Count trailing blank blocks
                blanks = 0
                blk = doc.lastBlock()
                while blk.isValid() and blk.text().strip() == '':
                    blanks += 1
                    blk = blk.previous()
                if blanks > 1:
                    c = self.terminal_output.textCursor()
                    c.movePosition(QTextCursor.End)
                    for _ in range(blanks - 1):
                        c.movePosition(QTextCursor.PreviousBlock, QTextCursor.KeepAnchor)
                    c.removeSelectedText()
            except Exception:
                pass

    def _write(self, text: str):
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.terminal_output.setTextCursor(cursor)

    def _replace_current_line(self, text: str):
        cursor = self.terminal_output.textCursor()
        # Remember start of the current block
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.StartOfBlock)
        block_start_pos = cursor.position()
        # Replace entire line content
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        cursor.insertText(text)
        self.terminal_output.setTextCursor(cursor)
        # Position caret within the line according to _line_cursor
        caret_pos = block_start_pos + min(max(self._line_cursor, 0), len(text))
        cursor = self.terminal_output.textCursor()
        cursor.setPosition(caret_pos)
        self.terminal_output.setTextCursor(cursor)

    def _render_current_line(self):
        self._replace_current_line(self._line_buffer)

    def _apply_zoom_in(self):
        try:
            self.terminal_output.zoomIn(1)
            self._zoom_steps += 1
        except Exception:
            pass

    def _apply_zoom_out(self):
        try:
            self.terminal_output.zoomOut(1)
            self._zoom_steps -= 1
        except Exception:
            pass

    def _apply_zoom_reset(self):
        try:
            if self._zoom_steps > 0:
                self.terminal_output.zoomOut(self._zoom_steps)
            elif self._zoom_steps < 0:
                self.terminal_output.zoomIn(-self._zoom_steps)
            self._zoom_steps = 0
        except Exception:
            pass

    def set_key_sender(self, sender_callable):
        """Provide a callable that will be used to send raw key data to SSH."""
        self._send_key = sender_callable
        # Flush any queued input collected before sender was ready
        if self._send_queue:
            try:
                self._send_key(''.join(self._send_queue))
            finally:
                self._send_queue.clear()

    def _send(self, data: str):
        if self._send_key is not None and data is not None:
            try:
                self._send_key(data)
            except Exception:
                # Silently ignore send errors in UI layer
                pass
        else:
            # Queue input until transport is ready
            if data:
                self._send_queue.append(data)

    def eventFilter(self, obj, event):
        if obj in (self.terminal_output, self.terminal_output.viewport()) and event.type() == QEvent.KeyPress:
            # Handle zoom shortcuts regardless of input mode
            key = event.key()
            modifiers = event.modifiers()
            if (modifiers & Qt.ControlModifier):
                # Ctrl + : zoom in (requires Shift on many layouts)
                if key == Qt.Key_Plus:
                    self.terminal_output.zoomIn(1)
                    self._zoom_steps += 1
                    return True
                # Ctrl - : zoom out
                if key == Qt.Key_Minus:
                    self.terminal_output.zoomOut(1)
                    self._zoom_steps -= 1
                    return True
                # Ctrl = : reset to default zoom
                if key == Qt.Key_Equal or key == Qt.Key_0:
                    if self._zoom_steps > 0:
                        self.terminal_output.zoomOut(self._zoom_steps)
                    elif self._zoom_steps < 0:
                        self.terminal_output.zoomIn(-self._zoom_steps)
                    self._zoom_steps = 0
                    return True
            if not self.input_enabled:
                return True if self.terminal_output.isReadOnly() else False
            # Ctrl+C
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_C:
                self._send("\x03")  # ETX
                return True
            # Ctrl+D
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_D:
                self._send("\x04")  # EOT
                return True
            # Ctrl+S should not freeze: send XOFF only if we really want to; otherwise ignore
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_S:
                # ignore to prevent terminal freeze
                return True
            # Enter / Return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                # Most PTYs expect CR; bash will map CR to NL via icrnl
                self._send("\r")
                return True
            # Backspace
            if key == Qt.Key_Backspace:
                # Send only DEL (erase = ^? per stty -a)
                self._send("\x7f")
                return True
            # Tab completion
            if key == Qt.Key_Tab:
                # Ask for one completion attempt
                self._send("\t")
                return True
            # Arrow keys and navigation as ANSI sequences
            if key == Qt.Key_Up:
                self._send("\x1b[A")
                return True
            if key == Qt.Key_Down:
                self._send("\x1b[B")
                return True
            if key == Qt.Key_Right:
                self._send("\x1b[C")
                return True
            if key == Qt.Key_Left:
                # Only send one left; do not perform any local deletion
                self._send("\x1b[D")
                return True
            if key == Qt.Key_Home:
                self._send("\x1b[H")
                return True
            if key == Qt.Key_End:
                self._send("\x1b[F")
                return True
            if key == Qt.Key_PageUp:
                self._send("\x1b[5~")
                return True
            if key == Qt.Key_PageDown:
                self._send("\x1b[6~")
                return True
            if key == Qt.Key_Delete:
                self._send("\x1b[3~")
                return True
            # Ctrl+L clear screen
            if (modifiers & Qt.ControlModifier) and key == Qt.Key_L:
                self._send("\x0c")
                return True
            # Printable characters
            text = event.text()
            if text:
                if self.local_echo_enabled:
                    self._write(text)
                self._send(text)
                return True
        return super().eventFilter(obj, event)

    def _strip_ansi(self, s: str) -> str:
        """Remove ANSI control sequences (CSI, OSC, etc.) so QTextEdit shows clean text."""
        # OSC sequences: ESC ] ... BEL or ESC \
        osc_pattern = re.compile(r"\x1B\][\x20-\x7E]*?(\x07|\x1B\\)")
        # CSI sequences: ESC [ ... Cmd
        csi_pattern = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        # Single-char ESC sequences
        esc_pattern = re.compile(r"\x1B[@-Z\\-_]")
        s = osc_pattern.sub('', s)
        s = csi_pattern.sub('', s)
        s = esc_pattern.sub('', s)
        return s

class TerminalTabs(QTabWidget):
    tab_close_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-top: none;
                background: white;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #ccc;
                border-bottom-color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
            }
        """)
        # We'll render our own close buttons so we keep native ones hidden
        self.setTabsClosable(False)
        self.tabCloseRequested.connect(self.on_tab_close)
        
    def on_tab_close(self, index):
        self.tab_close_requested.emit(index)
        
    def add_terminal_tab(self, session):
        tab = TerminalTab(session)
        display_name = getattr(session, 'name', None) or session.host
        tab_index = self.addTab(tab, f"🖥️ {display_name}")
        self.setCurrentIndex(tab_index)
        # Add faint cross button that becomes prominent on hover with red square
        self._add_close_button_to_tab(tab_index)
        return tab

    def add_sftp_tab(self, session, sftp_tab_widget: QWidget):
        display_name = getattr(session, 'name', None) or session.host
        tab_index = self.addTab(sftp_tab_widget, f"📁 {display_name}")
        self.setCurrentIndex(tab_index)
        self._add_close_button_to_tab(tab_index)
        return sftp_tab_widget
        
    def get_current_terminal(self):
        current_widget = self.currentWidget()
        if isinstance(current_widget, TerminalTab):
            return current_widget
        return None

    def _add_close_button_to_tab(self, index: int):
        btn = CloseButton(self)
        btn.clicked.connect(self._on_close_button_clicked)
        # Place the button on the right side of the tab
        self.tabBar().setTabButton(index, QTabBar.RightSide, btn)

    def _on_close_button_clicked(self):
        sender = self.sender()
        if not sender:
            return
        # Determine which tab owns this button
        bar = self.tabBar()
        for i in range(self.count()):
            if bar.tabButton(i, QTabBar.RightSide) is sender:
                self.on_tab_close(i)
                return