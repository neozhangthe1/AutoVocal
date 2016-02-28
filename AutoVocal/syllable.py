MS_PER_MINUTE = 60000


class Syllable:
    def __init__(self, pitch, relative_duration, tempo):
        self.pitch = pitch
        self.duration = relative_duration * MS_PER_MINUTE / tempo
