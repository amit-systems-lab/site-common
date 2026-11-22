#!/usr/bin/env python3
"""Plan an IndexNow submission for the URLs a deploy changes.

IndexNow (https://www.indexnow.org/documentation) tells Bing, Yandex,
Seznam, Naver and Yep that URLs were added, updated or deleted, so they
recrawl them now instead of at their next visit. Google does not use it.

Run in CI after `quarto render`, before the site is uploaded:

    python3 _common/scripts/indexnow.py

It writes `_site/indexnow-manifest.json` (a content hash for every page and
PDF, published with the site), fetches the manifest of the currently live
site, and diffs the two. The URLs that are new, changed or removed become
the request body, written to $GITHUB_OUTPUT as `body` (empty when there is
nothing to submit); the workflow POSTs it after the deploy succeeds.

A site opts in by committing its key file at the repository root,
`<key>.txt` containing just `<key>` (32 hex characters), and listing it
under `project: resources:` so it is published at the site root -- that is
how IndexNow verifies ownership. The key is public by design. Without a
key file the manifest is still written and nothing is submitted.

No previous manifest (404): every URL is submitted once. Live site not
answering (other errors, after retries): nothing is submitted, rather than
resubmitting the whole site.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
MANIFEST = "indexnow-manifest.json"
KEY_RE = re.compile(r"^[0-9a-f]{32}$")
SKIP_DIRS = {"site_libs", "_common", "bib"}
SKIP_FILES = {"404.html"}
# Quarto's built-in listing templates embed each source file's mtime, which
# a CI checkout resets on every run; it only feeds client-side sorting.
VOLATILE = re.compile(rb' data-listing-file-modified-sort="\d+"')


def site_url():
    m = re.search(r"^\s*site-url:\s*[\"']?([^\s\"']+)", Path("_quarto.yml").read_text(), re.M)
    if not m:
        sys.exit("indexnow: no site-url in _quarto.yml")
    return m.group(1).rstrip("/")


def find_key():
    keys = [p.stem for p in OUT.glob("*.txt")
            if KEY_RE.match(p.stem) and p.read_text().strip() == p.stem]
    if len(keys) > 1:
        sys.exit(f"indexnow: more than one key file in {OUT}/: {keys}")
    return keys[0] if keys else None


def manifest():
    """{site-relative URL path: sha256} for every published page and PDF."""
    entries = {}
    for p in sorted(OUT.rglob("*")):
        rel = p.relative_to(OUT)
        if (not p.is_file() or p.suffix not in (".html", ".pdf")
                or rel.parts[0] in SKIP_DIRS or rel.name in SKIP_FILES):
            continue
        path = "/" + rel.as_posix()
        if path.endswith("/index.html"):
            path = path[: -len("index.html")]
        data = p.read_bytes()
        if p.suffix == ".html":
            data = VOLATILE.sub(b"", data)
        entries[path] = hashlib.sha256(data).hexdigest()
    return entries


def live_manifest(base):
    """The deployed manifest; {} if there is none yet; None if unreachable."""
    url = f"{base}/{MANIFEST}"
    err = ""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            err = str(e)
        time.sleep(5 * (attempt + 1))
    print(f"indexnow: could not fetch {url} ({err}); submitting nothing")
    return None


def output(body):
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"body={body}\n")


def main():
    base = site_url()
    new = manifest()
    (OUT / MANIFEST).write_text(json.dumps(new, indent=0, sort_keys=True) + "\n")
    key = find_key()
    if not key:
        print(f"indexnow: wrote {MANIFEST} ({len(new)} URLs); no key file, not submitting")
        return output("")
    old = live_manifest(base)
    if old is None:
        return output("")
    changed = sorted(p for p in new.keys() | old.keys() if new.get(p) != old.get(p))
    print(f"indexnow: {len(new)} URLs, {len(changed)} new/changed/removed"
          + ("" if old else " (no previous manifest: submitting all)"))
    for p in changed:
        print(f"  {'removed ' if p not in new else ''}{p}")
    if not changed:
        return output("")
    host = base.split("://", 1)[1].split("/", 1)[0]
    output(json.dumps({
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": [base + p for p in changed][:10000],
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
