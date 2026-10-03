"""One browser, one agent at a time.

Two agents driving the same browser clobber each other's focus and fields,
which is unacceptable during real, irreversible submits. Every driver run holds
an exclusive non-blocking lock; a second run fails fast instead of interleaving.
"""
from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager


class BrowserBusy(RuntimeError):
    pass


@contextmanager
def browser_lock(workdir: str):
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "browser.lock")
    fh = open(path, "w")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BrowserBusy("another run is driving the browser; run applications "
                              "sequentially") from None
        fh.write(str(os.getpid()))
        fh.flush()
        yield
    finally:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()
