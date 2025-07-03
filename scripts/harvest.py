#!/usr/bin/env python3
"""
Harvest the PyPI 'Latest Updates' RSS feed, fetch per-release JSON metadata,
and append daily JSONL files under data/.
"""
import os, re, json, datetime
import feedparser, requests

RSS_URL = "https://pypi.org/rss/updates.xml"     # :contentReference[oaicite:0]{index=0}
JSON_TPL = "https://pypi.org/pypi/{pkg}/{ver}/json"  # :contentReference[oaicite:1]{index=1}
DATA_DIR = "data"
TS_FILE  = os.path.join(DATA_DIR, "last_timestamp.txt")

os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------------------------------------------ helpers
def iso_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def read_last_ts():
    if not os.path.exists(TS_FILE):
        return None
    with open(TS_FILE, "r") as f:
        return f.read().strip()

def write_last_ts(ts):
    with open(TS_FILE, "w") as f:
        f.write(ts)

# ------------------------------------------------------------------ main
feed = feedparser.parse(RSS_URL)
last_ts = read_last_ts()
new_items = []

for entry in feed.entries:
    # Example title: "awesome-lib 0.4.1"
    m = re.match(r"(?P<pkg>[A-Za-z0-9_.\-]+)\s+(?P<ver>[0-9a-zA-Z\.\-\+]+)", entry.title)
    if not m:
        continue
    published = entry.published  # e.g. 'Thu, 03 Jul 2025 17:12:34 GMT'
    if last_ts and published <= last_ts:
        continue  # already processed
    pkg, ver = m.group("pkg"), m.group("ver")

    try:
        meta = requests.get(JSON_TPL.format(pkg=pkg, ver=ver), timeout=15).json()
    except Exception as e:
        print(f"warn: failed {pkg}=={ver}: {e}")
        continue

    record = {
        "fetched_at": iso_now(),
        "published":  published,
        "package":    pkg,
        "version":    ver,
        "json":       meta,              # full PyPI JSON response
    }
    new_items.append(record)

# nothing new?
if not new_items:
    print("No fresh releases today.")
    exit(0)

outfile = os.path.join(
    DATA_DIR,
    f"releases-{datetime.date.today().isoformat()}.jsonl"
)
with open(outfile, "a") as f:
    for rec in new_items:
        f.write(json.dumps(rec) + "\n")

# persist newest timestamp for tomorrow’s delta
latest_pub = max(item["published"] for item in new_items)
write_last_ts(latest_pub)

print(f"Wrote {len(new_items)} releases to {outfile}")

