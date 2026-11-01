#!/usr/bin/env python3
"""Refresh the "Latest from the lab" section of the profile README.

Lists the most recently updated public repositories (not forks, not archived,
not this profile repository) between the markers

    <!-- LATEST:START --> ... <!-- LATEST:END -->

Run daily by .github/workflows/refresh-readme.yml. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = os.environ.get("GH_USER", "KiranKhann")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path(__file__).resolve().parents[1] / "README.md"
START, END = "<!-- LATEST:START -->", "<!-- LATEST:END -->"
HOW_MANY = 4
PKT = timezone(timedelta(hours=5), "PKT")

ICONS = {
    "Python": "🐍", "Jupyter Notebook": "📓", "JavaScript": "🟨", "TypeScript": "🔷",
    "HTML": "🌐", "CSS": "🎨", "Shell": "🐚", "Dockerfile": "🐳",
}


def api(path: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USER}-profile-readme"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def ago(timestamp: str, now: datetime) -> str:
    then = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    days = (now - then).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def cell(text: str) -> str:
    """Make free text safe inside a Markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def build_block(now: datetime) -> str:
    repos = api(f"/users/{USER}/repos?sort=pushed&direction=desc&per_page=50&type=owner")
    picks = [r for r in repos
             if not r.get("fork") and not r.get("private") and not r.get("archived")
             and r["name"].lower() != USER.lower()][:HOW_MANY]
    lines = ["| | Project | What it is | Updated |", "|:-:|:--|:--|:--|"]
    for r in picks:
        lang = r.get("language") or "Other"
        icon = ICONS.get(lang, "🛠️")
        desc = cell(r.get("description")) or "—"
        lines.append(f"| {icon} | **[{cell(r['name'])}]({r['html_url']})** | {desc} | {ago(r['pushed_at'], now)} |")
    stamp = now.astimezone(PKT).strftime("%d %b %Y, %H:%M PKT")
    lines += ["", f"<sub>🤖 This list updates itself every day through a GitHub Action · last refresh {stamp}</sub>"]
    return "\n".join(lines)


def main() -> int:
    now = datetime.now(timezone.utc)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("Markers not found in README.md; nothing to do.")
        return 1
    new_block = f"{START}\n{build_block(now)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: new_block, text, flags=re.S)
    if updated == text:
        print("No change.")
        return 0
    README.write_text(updated, encoding="utf-8")
    print("README.md updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
