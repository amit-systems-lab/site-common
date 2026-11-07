#!/usr/bin/env python3
"""Split publications.bib into one .bib file per entry under bib/.

Wired up as a Quarto pre-render step so the per-entry files are
available at /bib/<key>.bib on the rendered site (and downloadable
from the BibTeX icon on each publication listing/page).
"""
import os
import re
import sys
from pathlib import Path


class BibError(Exception):
    pass


def parse_entries(content):
    """Yield (key, raw_entry_text) for each top-level @entry{} in the bib content.

    Raises BibError on an unterminated entry. Braces are unbalanced from that
    point on, so an unclosed brace mid-file swallows every entry after it;
    stopping with a partial set would silently drop those papers' BibTeX
    files and DOI permalinks.
    """
    n = len(content)
    i = 0
    while i < n:
        at = content.find('@', i)
        if at < 0:
            return
        m = re.match(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', content[at:])
        if not m:
            i = at + 1
            continue
        key = m.group(2)
        brace = content.find('{', at)
        depth = 1
        j = brace + 1
        while j < n and depth > 0:
            c = content[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            j += 1
        if depth != 0:
            line = content.count('\n', 0, at) + 1
            raise BibError(f"unterminated entry {key!r} at line {line}")
        yield key, content[at:j]
        i = j


def project_dir():
    """The consuming site's project root.

    This script lives in the site-common submodule, so it must not derive
    the root from its own location. Quarto runs pre-render scripts with the
    project directory as the working directory and exports it as
    QUARTO_PROJECT_DIR; fall back to the cwd when run by hand.
    """
    env_dir = os.environ.get('QUARTO_PROJECT_DIR')
    return Path(env_dir).resolve() if env_dir else Path.cwd().resolve()


def main():
    repo_root = project_dir()
    src = repo_root / 'publications.bib'
    out_dir = repo_root / 'bib'

    if not src.exists():
        # Hard failure: a silent skip here ships a site whose BibTeX links
        # 404 and whose DOI permalinks silently disappear.
        print(f"split_bib: no {src} found", file=sys.stderr)
        return 1

    # Parse the whole file before touching bib/, so a bad input fails the
    # build without first deleting the previous output.
    content = src.read_text(encoding='utf-8')
    seen = {}
    try:
        for key, entry in parse_entries(content):
            if key in seen:
                raise BibError(f"duplicate key {key!r}")
            seen[key] = entry
    except BibError as e:
        print(f"split_bib: {src.name}: {e}", file=sys.stderr)
        return 1
    if not seen:
        print(f"split_bib: no entries found in {src}", file=sys.stderr)
        return 1

    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob('*.bib'):
        old.unlink()
    for key, entry in seen.items():
        (out_dir / f"{key}.bib").write_text(entry + "\n", encoding='utf-8')
    print(f"split_bib: wrote {len(seen)} entries to {out_dir.relative_to(repo_root)}/")
    return 0


if __name__ == '__main__':
    sys.exit(main())
