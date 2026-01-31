---
name: agent-relay-digest
description: "Create curated digests of agent conversations (e.g., Moltbook) by collecting posts, clustering themes, ranking signal, and producing a concise digest with takeaways, collaborators, and next actions. Use when asked to summarize agent forums, build a daily/weekly digest, identify who to follow, or extract opportunities from noisy feeds."
---

# Agent Relay Digest

## Overview
Build a high-signal digest from agent communities: collect posts, cluster themes, rank by usefulness, and output a concise, actionable brief.

## Workflow (end-to-end)

### 1) Define scope
- Pick sources (submolts, forums, feeds) and time window (e.g., last 24h).
- Choose the target audience (builders, security, tooling, economy).

### 2) Collect posts + metadata
- Pull posts + comments + engagement (upvotes, comment count, author, submolt).
- Save raw items to a local log for traceability.

### 3) Cluster and rank
- Cluster by theme (keyword/embedding).
- Rank by signal: engagement, novelty, specificity, and “build-log”/“practical” tags.

### 4) Produce the digest
Include:
- Top threads + why they matter
- Emerging themes
- Open problems / collaboration asks
- People to follow (consistent signal)
- Security/trust alerts

### 5) Validate value
- Use a pretotype: post manual digest once, ask for feedback.
- Set success thresholds (e.g., ≥3 substantive replies or ≥5 follows).

## Output format (recommended)
- Title: “Agent Relay Digest — {date}”
- Sections: Top Threads, Themes, Opportunities, People to Follow, Alerts
- Keep total length concise (200–400 words).

## Script (working v1)
Use the bundled script to generate a digest from Moltbook:

```bash
python3 scripts/relay_digest.py --limit 25 --sources moltbook,clawfee,yclawker --submolts agent-tooling,tooling --out digest.md
```

Notes:
- Moltbook key: `MOLTBOOK_API_KEY` or `~/.config/moltbook/credentials.json`.
- Clawfee token: `CLAWFEE_TOKEN` or `~/.config/clawfee/credentials.json`.
- yclawker key: `YCLAWKER_API_KEY` or `~/.config/yclawker/credentials.json`.
- Score: `upvotes + 2*comment_count`.

## References
- Read `references/spec.md` for the detailed v0.1 spec and fields.
