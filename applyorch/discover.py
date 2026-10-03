"""Discovery: fetch public ATS job boards, normalise, dedupe and score roles.

Deterministic and stdlib-only, so a recurring schedule costs no model tokens.
The script does the mechanical work; a cheap model (or a person) reviews only
the short digest of new top matches it prints.

Supported boards (all public, read-only JSON):
  greenhouse  https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
  ashby       https://api.ashbyhq.com/posting-api/job-board/{slug}
  lever       https://api.lever.co/v0/postings/{slug}?mode=json

With ``fixtures_dir`` set, boards are read from ``{fixtures_dir}/{ats}-{slug}.json``
instead of the network. The demo and the tests use that offline path.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "apply-orchestrator/1.0 (+discovery)"


def endpoint(target: dict) -> str | None:
    ats, slug = target["ats"], target.get("slug", "")
    if ats == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    if ats == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    if ats == "lever":
        return f"https://api.lever.co/v0/postings/{slug}?mode=json"
    return None


def fetch_json(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def load_board(target: dict, fixtures_dir: str | None = None):
    if endpoint(target) is None:
        raise ValueError("bespoke board: no public JSON endpoint (use a browser fallback)")
    if fixtures_dir:
        path = os.path.join(fixtures_dir, f"{target['ats']}-{target['slug']}.json")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return fetch_json(endpoint(target))


def normalize(company: str, ats: str, data) -> list[dict]:
    """Map each provider's payload onto one flat role record."""
    rows = []
    if ats == "greenhouse":
        for j in data.get("jobs", []):
            rows.append((j.get("title", ""), (j.get("location") or {}).get("name", ""),
                         j.get("absolute_url", ""),
                         ";".join(d.get("name", "") for d in j.get("departments", []))))
    elif ats == "ashby":
        for j in data.get("jobs", []):
            rows.append((j.get("title", ""), j.get("location", ""),
                         j.get("jobUrl") or j.get("applyUrl", ""),
                         j.get("team", "") or j.get("department", "")))
    elif ats == "lever":
        for j in data:
            cat = j.get("categories", {}) or {}
            rows.append((j.get("text", ""), cat.get("location", ""),
                         j.get("hostedUrl", ""), cat.get("team", "")))
    return [dict(company=company, provider=ats, title=t, location=loc, url=u, team=tm)
            for (t, loc, u, tm) in rows]


class Scorer:
    """Keyword-weight relevance model. Every weight comes from config, not code."""

    def __init__(self, cfg: dict):
        self.weights = [(re.compile(p, re.I), w) for p, w in cfg["keyword_weights"].items()]
        self.geo_ok = re.compile(cfg["geo_ok"], re.I)
        self.geo_gated = re.compile(cfg["geo_gated"], re.I)
        self.senior = re.compile(cfg["senior"], re.I)
        self.junior = re.compile(cfg["junior"], re.I)
        self.b = cfg.get("bonuses", {})

    def score(self, role: dict) -> int:
        hay = f"{role['title']} {role.get('team', '')}"
        s = sum(w for pat, w in self.weights if pat.search(hay))
        loc = role.get("location") or ""
        if self.geo_ok.search(loc):
            s += self.b.get("geo_ok", 6)
        elif self.geo_gated.search(loc):
            s += self.b.get("geo_gated", 2)  # possible with sponsorship, so not dropped
        if self.junior.search(role["title"]):
            s += self.b.get("junior", -8)
        if self.senior.search(role["title"]):
            s += self.b.get("senior", 2)
        return s


def dedupe_key(role: dict) -> str:
    def squash(x):
        return re.sub(r"[^a-z0-9]", "", (x or "").lower())
    raw = f"{role['company']}|{squash(role['title'])}|{squash(role.get('location'))}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def discover(targets: list[dict], cfg: dict, roles_path: str,
             fixtures_dir: str | None = None, now: str | None = None) -> dict:
    """Append only NEW roles at or above the threshold to ``roles_path`` (JSONL)."""
    scorer = Scorer(cfg)
    threshold = cfg.get("threshold", 8)
    seen = set()
    if os.path.exists(roles_path):
        with open(roles_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["dedupe_key"])
                except (ValueError, KeyError):
                    pass

    now = now or datetime.now(timezone.utc).isoformat()
    new, resolved, failed = [], [], []
    for t in targets:
        try:
            roles = normalize(t["company"], t["ats"], load_board(t, fixtures_dir))
        except Exception as e:  # one broken board must not stop the sweep
            failed.append((t["company"], str(e)[:80]))
            continue
        resolved.append((t["company"], len(roles)))
        for r in roles:
            r.update(dedupe_key=dedupe_key(r), score=scorer.score(r), first_seen=now,
                     priority=t.get("priority", ""))
            if r["dedupe_key"] not in seen and r["score"] >= threshold:
                seen.add(r["dedupe_key"])
                new.append(r)

    new.sort(key=lambda x: -x["score"])
    os.makedirs(os.path.dirname(os.path.abspath(roles_path)), exist_ok=True)
    with open(roles_path, "a", encoding="utf-8") as fh:
        for r in new:
            fh.write(json.dumps(r) + "\n")
    return {"new": new, "resolved": resolved, "failed": failed}


def digest(result: dict, top: int = 30) -> str:
    lines = [f"boards resolved: {len(result['resolved'])} | failed/bespoke: "
             f"{len(result['failed'])} | new relevant roles: {len(result['new'])}", "",
             "TOP NEW MATCHES"]
    for r in result["new"][:top]:
        lines.append(f"  [{r['score']:>3}] {r['company'][:24]:<24} {r['title'][:52]:<52} "
                     f"{(r.get('location') or '')[:24]}")
    for company, err in result["failed"]:
        lines.append(f"  x {company}: {err}")
    return "\n".join(lines)
