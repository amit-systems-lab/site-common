# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24", "pyyaml>=6"]
# ///
"""Fix up the published copies of paper PDFs: metadata, and an optional notice.

Every PDF linked from a paper page gets its document Title and Author set
from the page's front matter (slides and posters get "(slides)"/"(poster)"
appended). Search engines use the PDF Title as the result's title, and many
of the originals have none or a leftover like "mapsize5.eps".

ACM's author-posting terms ask that a self-hosted copy say it is the
authors' version, for personal use, not for redistribution, and point to
the definitive version. Papers opt in from their front matter:

    pdf-notice:
      venue: "ASPLOS '23"
      doi: 10.1145/3575693.3575716
      y: 34          # optional baseline, in points from the page bottom

Run as a Quarto post-render step (via _common/scripts/fix-pdfs.sh). Only the
copies under the output directory are changed; the PDFs in the repository
stay as they are, so the originals are never published.
"""
import os
import re
import sys
from pathlib import Path

import pymupdf
import yaml

FONT, SIZE, GREY = "helv", 7, (0.35, 0.35, 0.35)
LEAD = "Authors' version, posted for personal use; not for redistribution."
MIN_GAP = 6  # points of clearance between the notice and the lowest text


def pdf_jobs():
    """Return {pdf href: {"title", "author", "notice", "qmd"}} for linked PDFs."""
    jobs = {}
    for qmd in sorted(Path("publications").glob("*/*.qmd")):
        m = re.match(r"---\n(.*?)\n---", qmd.read_text(), re.S)
        meta = yaml.safe_load(m.group(1)) if m else None
        if not meta:
            continue
        links = [link for link in meta.get("links", [])
                 if link.get("href", "").startswith("/") and link["href"].endswith(".pdf")]
        papers = [link for link in links if link.get("text") == "PDF"]
        if "pdf-notice" in meta and len(papers) != 1:
            sys.exit(f"{qmd}: pdf-notice needs exactly one PDF link, found {len(papers)}")
        for link in links:
            kind = link.get("text", "")
            title = str(meta["title"]) + ("" if kind == "PDF" else f" ({kind.lower()})")
            job = {"title": title, "author": str(meta.get("author", "")), "qmd": qmd,
                   "notice": meta.get("pdf-notice") if kind == "PDF" else None}
            prev = jobs.get(link["href"])
            if prev and (prev["title"], prev["notice"]) != (job["title"], job["notice"]):
                sys.exit(f"{qmd}: {link['href']} is also linked from {prev['qmd']} as something else")
            jobs[link["href"]] = job
    return jobs


def stamp(doc, path, venue, doi, y=None):
    """Stamp page 1 of the open doc. Returns False if already stamped."""
    page = doc[0]
    if LEAD in page.get_text():
        return False
    rect = page.rect
    url = f"https://doi.org/{doi}"
    text = f"{LEAD} Definitive version: {venue}, "
    width = pymupdf.get_text_length(text + url, fontname=FONT, fontsize=SIZE)
    x = (rect.width - width) / 2
    if y is None:
        # Halfway between the page edge and the lowest text (the page
        # number, or the ACM rights block), but no higher than 18pt.
        bottoms = [w[3] for w in page.get_text("words") if w[1] >= 0 and w[3] <= rect.y1]
        floor = rect.height - max(bottoms)
        y = min(18, floor / 2 - SIZE / 3)
        if floor - (y + SIZE) < MIN_GAP:
            sys.exit(f"{path}: only {floor:.1f}pt below the text; set pdf-notice.y")
    base = rect.height - y  # PyMuPDF measures from the top
    page.insert_text((x, base), text + url, fontname=FONT, fontsize=SIZE, color=GREY)
    ux = x + pymupdf.get_text_length(text, fontname=FONT, fontsize=SIZE)
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "uri": url,
        "from": pymupdf.Rect(ux, base - SIZE, x + width, base + 1.5),
    })
    return True


def main():
    out = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    full = os.environ.get("QUARTO_PROJECT_RENDER_ALL") == "1"
    stamped = titled = 0
    for href, job in pdf_jobs().items():
        path = out / href.lstrip("/")
        if not path.exists():
            # A partial render need not have copied this PDF; a full one must.
            if full:
                sys.exit(f"{job['qmd']}: {path} is not in the rendered site")
            continue
        doc = pymupdf.open(path)
        changed = False
        notice = job["notice"]
        if notice and stamp(doc, path, notice["venue"], notice["doi"], notice.get("y")):
            stamped += 1
            changed = True
        meta = dict(doc.metadata or {})
        if (meta.get("title"), meta.get("author")) != (job["title"], job["author"]):
            meta.update(title=job["title"], author=job["author"])
            doc.set_metadata(meta)
            titled += 1
            changed = True
        if changed:
            tmp = f"{path}.tmp"
            doc.save(tmp, garbage=3, deflate=True, use_objstms=True, no_new_id=True)
            doc.close()
            os.replace(tmp, path)
        else:
            doc.close()
    print(f"fix_pdfs: stamped {stamped} PDF(s), set title on {titled}")


if __name__ == "__main__":
    main()
