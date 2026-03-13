"""
Simple loading spinner for CLI. Runs in background thread.
"""

import sys
import threading
import time

CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Spinner:
    def __init__(self, message: str = "Loading"):
        self.message = message
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin)
        self._thread.daemon = True
        self._thread.start()

    def _spin(self):
        i = 0
        while self._running:
            c = CHARS[i % len(CHARS)]
            sys.stdout.write(f"\r{self.message} {c} ")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)

    def stop(self, success: bool = True):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        mark = "✓" if success else "✗"
        sys.stdout.write(f"\r{self.message} {mark}\n")
        sys.stdout.flush()
