"""Per-role application packets.

A packet is one Markdown file per role, written before anything touches a form.
Sections (``## Heading``) the tooling reads:

  ## Role             key: value lines (company, title, ats, slug, hold)
  ## Apply URL        the form URL
  ## Form fields      a two-column table: label | value (overrides profile defaults)
  ## Cover letter     the letter, pasted verbatim into the cover-letter field
  ## Likely supplementary questions + answers   ### per question
  ## Resume to upload a repo-relative path
  ## Unverified claims I avoided   free text for the reviewer; never sent
  ## Revision log     free text; never sent

Everything outside the sendable sections is scaffolding for the human reviewer
and is never pasted into a form.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


def section(text: str, name: str) -> str:
    m = re.search(rf"^## {re.escape(name)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def clean_prose(block: str) -> str:
    """Strip authoring notes so they can never leak into a live form."""
    b = re.sub(r"^\s*\*\(.*?\)\*\s*$", "", block, flags=re.M)        # *(word count)* notes
    b = re.sub(r"^\s*\*[^*\n][^\n]*\*\s*$", "", b, flags=re.M)        # whole-line italic notes
    b = re.sub(r"^\s*---\s*$", "", b, flags=re.M)
    b = re.sub(r"^\s{0,3}>\s?", "", b, flags=re.M)                    # blockquote framing
    b = re.sub(r"\*\*(.+?)\*\*", r"\1", b)
    return re.sub(r"\n{3,}", "\n\n", b).strip()


@dataclass
class Packet:
    key: str
    path: str
    company: str
    title: str
    ats: str
    apply_url: str
    fields: dict = field(default_factory=dict)
    letter: str = ""
    qa: list = field(default_factory=list)
    resume: str = ""
    hold: str = ""

    def prose(self) -> list[tuple[str, str]]:
        """Every free-text string that will be sent, labelled."""
        out = [("cover_letter", self.letter)] if self.letter else []
        out += [(f"qa[{i}] {q}", a) for i, (q, a) in enumerate(self.qa)]
        out += [(f"field {k}", v) for k, v in self.fields.items() if len(v.split()) >= 12]
        return out

    def resume_path(self, root: str) -> str:
        return self.resume if os.path.isabs(self.resume) else os.path.join(root, self.resume)


def _kv(block: str) -> dict:
    out = {}
    for line in block.splitlines():
        m = re.match(r"^\s*[-*]?\s*([A-Za-z_ ]+?)\s*:\s*(.+?)\s*$", line)
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def parse(path: str) -> Packet:
    with open(path, encoding="utf-8") as fh:
        t = fh.read()
    role = _kv(section(t, "Role"))
    url_m = re.search(r"https?://\S+", section(t, "Apply URL"))

    fields = {}
    for label, value in re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
                                   section(t, "Form fields"), re.M):
        label = re.sub(r"\*\*|`", "", label).strip()
        value = re.sub(r"\*\*|`", "", value).strip()
        if set(label) <= set("-: ") or set(value) <= set("-: "):
            continue
        if label.lower() == "field" and value.lower() == "value":
            continue
        fields[label] = value

    qa = []
    for blk in re.split(r"^### ", section(t, "Likely supplementary questions + answers"),
                        flags=re.M)[1:]:
        head, _, body = blk.strip().partition("\n")
        q = re.sub(r"^\d+\.\s*", "", head)
        q = re.sub(r"\*\(.*?\)\*", "", q).replace("*", "").strip()
        a = clean_prose(body)
        if q and a:
            qa.append((q, a))

    resume_m = re.search(r"`([^`]+)`", section(t, "Resume to upload"))
    return Packet(
        key=os.path.splitext(os.path.basename(path))[0],
        path=path,
        company=role.get("company", ""),
        title=role.get("title", ""),
        ats=role.get("ats", ""),
        apply_url=url_m.group(0).rstrip(")") if url_m else "",
        fields=fields,
        letter=clean_prose(section(t, "Cover letter")),
        qa=qa,
        resume=resume_m.group(1) if resume_m else "",
        hold=role.get("hold", ""),
    )


def load_all(directory: str) -> list[Packet]:
    return [parse(os.path.join(directory, f)) for f in sorted(os.listdir(directory))
            if f.endswith(".md") and not f.startswith("_")]
