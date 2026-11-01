"""Cooperative external input schedule; caller must observe before each step."""


class ChatSequence:
    def __init__(self, text, now, timeout=8):
        if not text.startswith('/') or '\n' in text or '\r' in text:
            raise ValueError('one slash command required')
        self.text = text
        self.deadline = now + timeout
        self.due = now
        self.stage = 'open'
        self.index = 0
        self.cancelled = False
        self.submitted = False

    def cancel(self):
        self.cancelled = True

    def step(self, now, permitted):
        if self.cancelled or self.submitted:
            return None
        if not permitted or now > self.deadline:
            self.cancel()
            raise ValueError('input sequence aborted')
        if now < self.due:
            return None
        if self.stage == 'open':
            self.stage, self.due = 'text', now + .8
            return ('key', 13)
        if self.stage == 'text':
            character = self.text[self.index]
            self.index += 1
            self.due = now + .05
            if self.index == len(self.text):
                self.stage, self.due = 'submit', now + .5
            return ('char', character)
        self.submitted = True
        return ('key', 13)


def spell_result(before, after, spell_id):
    if after['cast_failed'] != before['cast_failed'] or after['ui_errors'] != before['ui_errors']:
        return 'FAILED'
    delta = (after['cast_succeeded'] - before['cast_succeeded']) % 65536
    if delta == 0:
        return 'PENDING'
    if delta != 1 or after['event_spell'] != spell_id or after['event_kind'] != 2:
        return 'AMBIGUOUS'
    return 'SUCCEEDED'
