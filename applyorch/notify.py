"""Push notification: exactly one per application actually SENT.

Fired only after the driver reports a submission AND the confirmation text was
seen. Channels, chosen from the environment at run time:

  BARK_URL   iOS push via Bark, e.g. https://api.day.app/<device-key>
  NTFY_URL   ntfy topic URL, e.g. https://ntfy.sh/<your-private-topic>
  (neither)  printed to stdout

The URL is a secret (it contains the device key or private topic). It is read
from the environment or keychain only, never written to a tracked file, a log,
the ledger, or an error message.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class Notifier:
    channel = "base"

    def send(self, title: str, body: str) -> bool:
        raise NotImplementedError


class StdoutNotifier(Notifier):
    channel = "stdout"

    def send(self, title, body):
        print(f"[notify] {title}: {body}")
        return True


class OutboxNotifier(Notifier):
    """Mock channel: appends to a local JSONL file so tests can assert on it."""
    channel = "outbox"

    def __init__(self, path: str):
        self.path = path

    def send(self, title, body):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"title": title, "body": body}) + "\n")
        return True


class BarkNotifier(Notifier):
    channel = "bark"

    def __init__(self, base_url: str, opener=urllib.request.urlopen):
        self._base = base_url.rstrip("/")
        self._open = opener

    def url_for(self, title: str, body: str) -> str:
        q = urllib.parse.quote
        return f"{self._base}/{q(title, safe='')}/{q(body, safe='')}"

    def send(self, title, body):
        try:
            with self._open(self.url_for(title, body), timeout=15) as r:
                return 200 <= getattr(r, "status", 200) < 300
        except Exception as e:  # never echo the URL: it carries the device key
            print(f"[notify] bark failed ({type(e).__name__}); key withheld from log")
            return False

    def __repr__(self):
        return "BarkNotifier(<redacted>)"


class NtfyNotifier(Notifier):
    channel = "ntfy"

    def __init__(self, topic_url: str, opener=urllib.request.urlopen):
        self._url = topic_url
        self._open = opener

    def send(self, title, body):
        req = urllib.request.Request(self._url, data=body.encode(), method="POST",
                                     headers={"Title": title})
        try:
            with self._open(req, timeout=15) as r:
                return 200 <= getattr(r, "status", 200) < 300
        except Exception as e:
            print(f"[notify] ntfy failed ({type(e).__name__}); topic withheld from log")
            return False

    def __repr__(self):
        return "NtfyNotifier(<redacted>)"


def from_env(env=None) -> Notifier:
    env = os.environ if env is None else env
    if env.get("BARK_URL"):
        return BarkNotifier(env["BARK_URL"])
    if env.get("NTFY_URL"):
        return NtfyNotifier(env["NTFY_URL"])
    return StdoutNotifier()
