"""
A serial version clock that works across multiple processes.
"""

import multiprocessing

class VersionClock(object):
    TYPECODE = "i"

    def __init__(self):
        self.lock = multiprocessing.RLock()
        self.value = multiprocessing.Value("i", 0)

    def _read(self):
        with self.lock:
            self.value.value += 1
            return self.value.value

    @classmethod
    def read(cls):
        return cls.GLOBAL._read()

VersionClock.GLOBAL = VersionClock()
