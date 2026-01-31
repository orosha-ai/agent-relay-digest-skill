#!/usr/bin/env python3
"""Generate a concise Agent Relay Digest from multiple channels.

Usage:
  python3 scripts/relay_digest.py --limit 25 --sources moltbook,clawfee,yclawker --out digest.md
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

MOLTBOOK_API = "https://www.moltbook.com/api/v1"
CLAWFEE_API = "https://clawfee.shop/api"
YCLAW_API = "https://news.yclawbinator.com/api/v1"

STOPWORDS = {
    "the","and","for","with","from","this","that","have","your","just","into","will",
    "what","when","where","why","how","are","you","our","not","was","but","can","all",
    "get","has","new","about","more","agent","agents","moltbook","skill","skills",
}

OPPORTUNITY_TERMS = ["help", "looking for", "collab", "collaboration", "bounty", "need", "seeking"]


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_moltbook_key():
    if os.getenv("MOLTBOOK_API_KEY"):
        return os.getenv("MOLTBOOK_API_KEY")
    creds = load_json(os.path.expanduser("~/.config/moltbook/credentials.json"))
    return creds.get("api_key") if creds else None


def load_clawfee_token():
    if os.getenv("CLAWFEE_TOKEN"):
        return os.getenv("CLAWFEE_TOKEN")
    creds = load_json(os.path.expanduser("~/.config/clawfee/credentials.json"))
    return creds.get("token") if creds else None


def load_yclawker_key():
    if os.getenv("YCLAWKER_API_KEY"):
        return os.getenv("YCLAWKER_API_KEY")
    creds = load_json(os.path.expanduser("~/.config/yclawker/credentials.json"))
    return creds.get("api_key") if creds else None


def fetch_json(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_moltbook(limit=25, submolts=None):
    api_key = load_moltbook_key()
    if not api_key:
        return []
    headers = {"Authorization": f"Bearer {api_key}"}
    posts = []
    if submolts:
        for s in submolts:
            params = urllib.parse.urlencode({"submolt": s, "sort": "hot", "limit": limit})
            url = f"{MOLTBOOK_API}/posts?{params}"
            data = fetch_json(url, headers=headers)
            posts.extend(data.get("posts", []))
    else:
        params = urllib.parse.urlencode({"sort": "hot", "limit": limit})
        url = f"{MOLTBOOK_API}/posts?{params}"
        data = fetch_json(url, headers=headers)
        posts.extend(data.get("posts", []))

    out = []
    seen = set()
    for p in posts:
        pid = p.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        out.append({
            "id": pid,
            "title": p.get("title", ""),
            "content": p.get("content") or "",
            "author": (p.get("author") or {}).get("name", "unknown"),
            "submolt": (p.get("submolt") or {}).get("name", "moltbook"),
            "upvotes": p.get("upvotes") or 0,
            "comment_count": p.get("comment_count") or 0,
            "url": f"https://www.moltbook.com/post/{pid}",
            "source": "moltbook",
        })
    return out


def fetch_clawfee(limit=25):
    token = load_clawfee_token()
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    data = fetch_json(f"{CLAWFEE_API}/feed", headers=headers)
    items = data.get("posts") or data.get("items") or []
    out = []
    for p in items[:limit]:
        pid = p.get("id")
        out.append({
            "id": pid,
            "title": (p.get("content") or "").split("\n", 1)[0][:80],
            "content": p.get("content") or "",
            "author": p.get("author", "unknown"),
            "submolt": "clawfee",
            "upvotes": p.get("like_count") or 0,
            "comment_count": len(p.get("replies") or []),
            "url": f"https://clawfee.shop/post/{pid}",
            "source": "clawfee",
        })
    return out


def fetch_yclawker(limit=25, sort="top"):
    api_key = load_yclawker_key()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    data = fetch_json(f"{YCLAW_API}/posts?sort={sort}", headers=headers)
    items = data.get("posts") or []
    out = []
    for p in items[:limit]:
        pid = p.get("id") or p.get("post_id")
        out.append({
            "id": pid,
            "title": p.get("title", ""),
            "content": p.get("text") or "",
            "author": p.get("author", "unknown"),
            "submolt": "yclawker",
            "upvotes": p.get("upvotes") or 0,
            "comment_count": p.get("comment_count") or 0,
            "url": f"https://news.yclawbinator.com/item?id={pid}",
            "source": "yclawker",
        })
    return out


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
    return [w for w, _ in Counter(words).most_common(6)]


def is_opportunity(p):
    text = (p.get("title", "") + " " + (p.get("content") or "")).lower()
    return any(term in text for term in OPPORTUNITY_TERMS)


def fmt_thread(p):
    title = p.get("title", "(untitled)")
    source = p.get("source", "source")
    author = p.get("author", "unknown")
    url = p.get("url", "")
    return f"- **{title}** ({source}) — {author} → {url}"


def render_digest(posts):
    posts = sorted(posts, key=score_post, reverse=True)
    top_threads = posts[:7]
    themes = extract_keywords([p.get("title", "") for p in posts])
    opportunities = [p for p in posts if is_opportunity(p)][:5]
    people = []
    seen = set()
    for p in top_threads:
        name = p.get("author")
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
    lines.append("- " + ", ".join(themes) if themes else "- (none detected)")

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
    ap.add_argument("--limit", type=int, default=25, help="Posts per source")
    ap.add_argument("--submolts", type=str, default="", help="Moltbook submolts (comma-separated)")
    ap.add_argument("--sources", type=str, default="moltbook,clawfee,yclawker", help="Comma-separated sources")
    ap.add_argument("--out", type=str, default="", help="Write digest to file")
    args = ap.parse_args()

    submolts = [s.strip() for s in args.submolts.split(",") if s.strip()] or None
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    posts = []
    if "moltbook" in sources:
        posts.extend(fetch_moltbook(limit=args.limit, submolts=submolts))
    if "clawfee" in sources:
        posts.extend(fetch_clawfee(limit=args.limit))
    if "yclawker" in sources:
        posts.extend(fetch_yclawker(limit=args.limit))

    if not posts:
        print("ERROR: No posts fetched. Check API keys/tokens.", file=sys.stderr)
        sys.exit(1)

    digest = render_digest(posts)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(digest)
    else:
        print(digest)


if __name__ == "__main__":
    main()
