#!/usr/bin/env python3
"""Fail the build when a rendered page links to something that is not there.

Both site-breaking bugs this repo has shipped were of this shape and both
built green: a pre-render step that stopped writing bib/, so every
/bib/<key>.bib link 404'd, and a publication entry whose PDF was never
committed. Neither is visible in a diff -- the link and the file are in
different places, and the file is usually absent rather than changed.

Checks the RENDERED site, not the sources, so it also covers resources that
Quarto was supposed to copy and did not.
"""
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Attributes worth following. `srcset` is deliberately absent: it is a
# comma-separated descriptor list, not a URL.
ATTRS = {'href', 'src', 'data-src', 'poster'}
SKIP_SCHEMES = ('http:', 'https:', 'mailto:', 'tel:', 'data:', 'javascript:', 'ftp:', '//')


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ATTRS and value:
                self.found.append(value.strip())


def targets(html_path, site_root):
    parser = Links()
    parser.feed(html_path.read_text(encoding='utf-8', errors='replace'))
    for raw in parser.found:
        if raw.startswith('#') or raw.lower().startswith(SKIP_SCHEMES):
            continue
        # Drop query and fragment; keep percent-decoding for paths with spaces.
        path = unquote(urlsplit(raw).path)
        if not path:
            continue
        base = site_root if path.startswith('/') else html_path.parent
        yield raw, (base / path.lstrip('/')).resolve()


def main():
    site_root = Path(os.environ.get('QUARTO_PROJECT_OUTPUT_DIR', '_site')).resolve()
    if not site_root.is_dir():
        print(f"check_links: no rendered site at {site_root}", file=sys.stderr)
        return 1

    broken, checked = [], 0
    for html in sorted(site_root.rglob('*.html')):
        for raw, target in targets(html, site_root):
            checked += 1
            # A link to a directory is served by its index.html.
            ok = target.is_file() or (target.is_dir() and (target / 'index.html').is_file())
            if not ok:
                broken.append((html.relative_to(site_root), raw))

    if broken:
        print(f"check_links: {len(broken)} broken link(s):", file=sys.stderr)
        for page, raw in broken:
            print(f"  {page} -> {raw}", file=sys.stderr)
            print(f"::error file={page}::links to {raw}, which is not in the rendered site")
        return 1

    print(f"check_links: {checked} local links across "
          f"{sum(1 for _ in site_root.rglob('*.html'))} pages, all resolve")
    return 0


if __name__ == '__main__':
    sys.exit(main())
