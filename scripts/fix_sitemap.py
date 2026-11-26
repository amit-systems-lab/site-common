#!/usr/bin/env python3
"""Quarto post-render: list directory pages in sitemap.xml as ".../", not
".../index.html".

Quarto's sitemap names the home page https://<site>/index.html, while its
canonical-url (and IndexNow) call it https://<site>/. Google treats the two
as different URLs, so the home page never gets credit for being in the
sitemap ("No referring sitemaps detected" in Search Console). Rewriting the
sitemap's <loc> entries makes all three agree. Standard library only.
"""
import os
import re
import sys
from pathlib import Path

out_dir = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
sitemap = out_dir / "sitemap.xml"
if not sitemap.is_file():
    sys.exit(0)  # partial render (quarto preview) or no site-url: nothing to fix

text = sitemap.read_text(encoding="utf-8")
fixed, n = re.subn(r"(<loc>[^<]*/)index\.html(</loc>)", r"\1\2", text)
if n:
    sitemap.write_text(fixed, encoding="utf-8")
    print(f"fix_sitemap: {n} index.html URL(s) rewritten to directory form")
