import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo")
sys.path.insert(0, ROOT)


def load(*parts):
    with open(os.path.join(DEMO, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def config():
    with open(os.path.join(ROOT, "config", "pipeline.example.json"), encoding="utf-8") as fh:
        return json.load(fh)
