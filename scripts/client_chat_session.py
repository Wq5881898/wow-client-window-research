"""Chat input that confirms the client actually accepted the text.

The probe reports whether the chat edit box is open, so the driver can tell
"the key was sent" from "the command reached the client".
"""
import time
import win32con
import win32gui
import lab_driver5 as d


class ChatSession:
    """Types a slash command in small steps and verifies the client state."""

    def __init__(self, hwnd, reader, key_delay=0.05, char_delay=0.06):
        self.hwnd = hwnd
        self.reader = reader          # callable returning the decoded state
        self.key_delay = key_delay
        self.char_delay = char_delay

    def _state(self):
        return self.reader()

    def open_chat(self, timeout=3.0):
        """Open the chat input and confirm it is actually open."""
        deadline = time.monotonic() + timeout
        state = self._state()
        if state.get('chat_open'):
            return True
        d.post_key(self.hwnd, win32con.VK_RETURN)
        while time.monotonic() < deadline:
            time.sleep(0.15)
            if self._state().get('chat_open'):
                return True
        raise ValueError('chat input did not open')
    def type_text(self, text):
        for character in text:
            win32gui.PostMessage(self.hwnd, win32con.WM_CHAR, ord(character), 0)
            time.sleep(self.char_delay)

    def submit(self, verify_closed=True, timeout=3.0):
        """Send the text and press Enter, then confirm the chat closed."""
        d.post_key(self.hwnd, win32con.VK_RETURN)
        if not verify_closed:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.15)
            if not self._state().get('chat_open'):
                return
        raise ValueError('chat input stayed open after submit')

    def run(self, text):
        """Full cycle: open, type, submit. Returns the state after submit."""
        self.open_chat()
        self.type_text(text)
        time.sleep(0.3)
        self.submit()
        return self._state()
