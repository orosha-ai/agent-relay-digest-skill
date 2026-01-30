#!/usr/bin/env python3
"""Generate a concise Agent Relay Digest from Moltbook posts.

Usage:
  python3 scripts/relay_digest.py --limit 25 --submolts agent-tooling,tooling --out digest.md
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

API_BASE = "https://www.moltbook.com/api/v1"

STOPWORDS = {
    "the","and","for","with","from","this","that","have","your","just","into","will",
    "what","when","where","why","how","are","you","our","not","was","but","can","all",
    "get","has","new","about","more","agent","agents","moltbook","skill","skills",
}

OPPORTUNITY_TERMS = ["help", "looking for", "collab", "collaboration", "bounty", "need", "seeking"]


def load_api_key():
    if os.getenv("MOLTBOOK_API_KEY"):
        return os.getenv("MOLTBOOK_API_KEY")
    cred_path = os.path.expanduser("~/.config/moltbook/credentials.json")
    if os.path.exists(cred_path):
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                return json.load(f).get("api_key")
        except Exception:
            return None
    return None


def fetch_json(url, api_key, timeout=20):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_posts(api_key, limit=25, submolts=None):
    posts = []
    if submolts:
        for s in submolts:
            params = urllib.parse.urlencode({"submolt": s, "sort": "hot", "limit": limit})
            url = f"{API_BASE}/posts?{params}"
            data = fetch_json(url, api_key)
            posts.extend(data.get("posts", []))
    else:
        params = urllib.parse.urlencode({"sort": "hot", "limit": limit})
        url = f"{API_BASE}/posts?{params}"
        data = fetch_json(url, api_key)
        posts.extend(data.get("posts", []))

    # Deduplicate by id
    seen = {}
    for p in posts:
        pid = p.get("id")
        if pid and pid not in seen:
            seen[pid] = p
    return list(seen.values())


def score_post(p):
    return (p.get("upvotes") or 0) + 2 * (p.get("comment_count") or 0)


def extract_keywords(titles):
    words = []
    for t in titles:
        for w in re.findall(r"[a-zA-Z0-9']+", t.lower()):
            if len(w) <= 3:
                continue
            if w in STOPWORDS:
                continue
            words.append(w)
    return [w for w, _ in Counter(words).most_common(5)]


def is_opportunity(p):
    text = (p.get("title", "") + " " + (p.get("content") or "")).lower()
    return any(term in text for term in OPPORTUNITY_TERMS)


def fmt_thread(p):
    title = p.get("title", "(untitled)")
    url = f"https://www.moltbook.com/post/{p.get('id')}"
    sub = (p.get("submolt") or {}).get("name", "unknown")
    author = (p.get("author") or {}).get("name", "unknown")
    return f"- **{title}** (m/{sub}) — {author} → {url}"


def render_digest(posts):
    posts = sorted(posts, key=score_post, reverse=True)
    top_threads = posts[:7]
    themes = extract_keywords([p.get("title", "") for p in posts])
    opportunities = [p for p in posts if is_opportunity(p)][:5]
    people = []
    seen = set()
    for p in top_threads:
        name = (p.get("author") or {}).get("name")
        if name and name not in seen:
            seen.add(name)
            people.append(name)
        if len(people) >= 5:
            break

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# Agent Relay Digest — {now}\n")
    lines.append("## Top Threads")
    for p in top_threads:
        lines.append(fmt_thread(p))

    lines.append("\n## Themes")
    if themes:
        lines.append("- " + ", ".join(themes))
    else:
        lines.append("- (none detected)")

    lines.append("\n## Opportunities")
    if opportunities:
        for p in opportunities:
            lines.append(fmt_thread(p))
    else:
        lines.append("- (none detected)")

    lines.append("\n## People to Follow")
    if people:
        for name in people:
            lines.append(f"- {name}")
    else:
        lines.append("- (none detected)")

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25, help="Number of posts to fetch per source")
    ap.add_argument("--submolts", type=str, default="", help="Comma-separated submolts")
    ap.add_argument("--out", type=str, default="", help="Write digest to file")
    args = ap.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("ERROR: Missing MOLTBOOK_API_KEY or ~/.config/moltbook/credentials.json", file=sys.stderr)
        sys.exit(1)

    submolts = [s.strip() for s in args.submolts.split(",") if s.strip()] or None
    posts = fetch_posts(api_key, limit=args.limit, submolts=submolts)
    digest = render_digest(posts)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(digest)
    else:
        print(digest)


if __name__ == "__main__":
    main()
