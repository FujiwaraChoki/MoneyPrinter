import json
import queue
import re
import time


class LogStream:
    """Thread-safe log queue that doubles as an SSE generator."""

    def __init__(self, maxsize: int = 500):
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)

    def clear(self) -> None:
        """Drain all pending items from the queue."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def push(self, message: str, level: str = "info") -> None:
        """Add a log entry. Drops the oldest entry if the queue is full."""
        entry = {
            "type": "log",
            "message": message,
            "level": level,
            "timestamp": time.time(),
        }
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                pass

    def push_event(self, event_type: str, data: dict | None = None) -> None:
        """Send a control event (complete, error, cancelled)."""
        entry = {
            "type": event_type,
            "timestamp": time.time(),
            **(data or {}),
        }
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                pass

    def stream(self, timeout: float = 30.0):
        """Generator yielding SSE-formatted lines. Terminates on control events."""
        while True:
            try:
                entry = self._queue.get(timeout=timeout)
                yield f"data: {json.dumps(entry)}\n\n"
                if entry.get("type") in ("complete", "error", "cancelled"):
                    return
            except queue.Empty:
                # Send keepalive comment to prevent connection timeout
                yield ": keepalive\n\n"


# Strip ANSI escape codes from terminal-colored strings
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Singleton shared by all modules
log_stream = LogStream()

# Color-to-level mapping for termcolor colors
_COLOR_LEVEL = {
    "green": "success",
    "red": "error",
    "yellow": "warning",
    "blue": "info",
    "cyan": "info",
    "magenta": "info",
}


def log(message: str, level: str = "info") -> None:
    """Drop-in replacement for ``print(colored(msg, color))``.

    Prints to the terminal **and** pushes an ANSI-stripped copy to the SSE queue.
    """
    print(message)
    clean = _ANSI_RE.sub("", str(message))
    log_stream.push(clean, level)
