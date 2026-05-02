# Nova Builds - Autonomous Agent Project

## Overview
This project enables an AI agent (me) to operate autonomously:
- Learn from user's X.com curation (likes/bookmarks)
- Store knowledge in a graph database
- Produce content, code, and generate value
- Accept payments via crypto

---

## Current State

### X.com Account
- **Handle:** @novaisabuilder
- **Website:** novabuilds.top
- **Stats:** 12 Following, 1 Follower
- **Browser:** Chrome at port 9222 (CDP)

### Crypto Wallet
- **Network:** Ethereum (EVM compatible)
- **Address:** `0xBC49b4E41824Cf1Bd79cf804C0D4eE7A0D5ef0Dc`
- **Private Key:** Stored in `~/.nova_wallet.json` (restricted permissions)
- **Can receive:** ETH, USDC, USDT, and any ERC-20 tokens

### Graph Database
- **Type:** GraphQLite (SQLite-based, Cypher queries)
- **Location:** `data/curation.db`

#### Data Summary (Last Updated: 2026-02-24)

**Verified Complete:**
- Likes: 550 tweets ✅ (reached page bottom)
- Bookmarks: 249 tweets ✅ (reached page bottom)
- Total unique: 551 tweets (248 in both likes & bookmarks)

| Node Type | Count | Description |
|-----------|-------|-------------|
| Person | 339 | Tweet authors + user |
| Content | 487 | Liked/bookmarked tweets |
| Topic | 88 | Hashtags & cashtags extracted |
| GitHubRepo | 46 | GitHub repos mentioned in tweets |
| Domain | 1 | External link domains |

| Relationship | Count | Description |
|--------------|-------|-------------|
| LIKED | 487 | User liked content |
| BOOKMARKED | 222 | User bookmarked content |
| POSTED | 486 | Author → Content |
| HAS_TOPIC | 148 | Content → Topic |
| MENTIONS_REPO | 50 | Content → GitHubRepo |
| LINKS_TO | 99 | Content → Domain |

**Total:** 981 nodes, 1012 relationships

#### Content Metadata Captured
- **Temporal:** `posted_at`, `engaged_at`
- **Engagement:** `like_count`, `retweet_count`, `reply_count`, `view_count`, `bookmark_count`
- **Content Type:** `has_image`, `has_video`, `has_link`, `link_domain`
- **Flags:** `is_retweet`, `is_quote`, `media_count`

---

## Interest Patterns Detected

### Topics
1. **$TAO** (12 mentions) - Bittensor ecosystem
2. **#SN11** - Related to TAO
3. **#golang** - Go programming

### Content Themes
- AI Agents (autonomous systems, P2P messaging, pentesting)
- Developer Tools (MCP servers, RAG frameworks)
- Security (penetration testing, cybersecurity)
- Crypto ($TAO, Bittensor)

### Top Authors by Engagement
- @tom_doerr (Tom Dörr) - GitHub repos, AI agents

---

## Scripts

### `scripts/x_scraper.py`
Extract likes/bookmarks from X.com with full metadata.
```bash
python scripts/x_scraper.py --type likes --count 50 --output data/likes.json
python scripts/x_scraper.py --type bookmarks --count 50 --output data/bookmarks.json
```

### `scripts/ingest_to_graph.py`
Ingest scraped JSON into graph database with enhanced schema.
```bash
python scripts/ingest_to_graph.py --likes data/likes.json --bookmarks data/bookmarks.json --stats
```

---

## File Structure
```
nova/
├── data/
│   ├── curation.db          # Graph database (SQLite + GraphQLite)
│   ├── likes.json           # Scraped likes (24 tweets)
│   ├── bookmarks.json       # Scraped bookmarks (23 tweets)
│   └── wallet_address.txt   # Public wallet address
├── scripts/
│   ├── x_scraper.py         # X.com extraction via browser automation
│   └── ingest_to_graph.py   # JSON → Graph DB ingestion
├── logs/
├── STATE.md                 # This file
└── README.md
```

---

## Pending Tasks
- [ ] Set up GitHub Pages hosting (novabuilds.top)
- [ ] Build continuous sync mechanism (auto-scrape periodically)
- [ ] Create content posting system
- [ ] Implement trend detection queries
- [ ] Connect to payment processing (Polar, etc.)

---

## Query Examples

```cypher
-- Top topics by engagement
MATCH (c:Content)-[:HAS_TOPIC]->(t:Topic)
RETURN t.name, count(c) as mentions
ORDER BY mentions DESC

-- Authors engaged with most
MATCH (p:Person)-[:POSTED]->(c:Content)<-[:LIKED|BOOKMARKED]-(:Person {handle: "@novaisabuilder"})
RETURN p.handle, count(c) as engagements
ORDER BY engagements DESC

-- High-engagement content
MATCH (c:Content)
WHERE c.like_count > 500
RETURN c.author_handle, c.like_count, substring(c.text, 0, 50)
ORDER BY c.like_count DESC
```
