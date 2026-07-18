# site-common

Shared infrastructure for the amit.zone Quarto sites:
[nadav.amit.zone](https://github.com/anadav) (personal) and
[lab.amit.zone](https://github.com/amit-systems-lab/lab-site) (lab).
Consumed by each site as a **git submodule at `_common/`** (the leading
underscore keeps Quarto from rendering these files into the site).

## Contents

| Path | What | Wired up via |
|---|---|---|
| `scripts/split_bib.py` | Splits `publications.bib` into per-paper `bib/<key>.bib` | `project: pre-render: _common/scripts/split_bib.py` |
| `filters/render-publication-links.lua` | Venue + PDF/Code/Permalink/BibTeX links on publication pages | `format: html: filters:` |
| `templates/bib-template.ejs` | Publications listing template | `listing: template:` in publications.qmd |
| `css/base.css` | Shared styles consuming `--site-*` variables | `format: html: css: [_common/css/base.css, styles.css]` |
| `includes/dark-mode-head.html` | Pre-paint dark marker (no white flash) | `format: html: include-in-header:` |
| `.github/workflows/quarto-publish.yml` | Reusable build+Pages-deploy workflow; **pins the Quarto version for all sites** | `jobs: publish: uses: amit-systems-lab/site-common/.github/workflows/quarto-publish.yml@master` |

## Site-side configuration

- **Author highlighting**: the listing template underlines authors named in
  the `highlight-authors` metadata list — set it in the site's
  `publications/_metadata.yml` (personal site: just Nadav; lab site: all
  members).
- **Palette**: each site's `styles.css` defines the `--site-*` variables in
  two blocks (`:root, body.quarto-light` and
  `html.site-pre-dark, body.quarto-dark`). See the header comment in
  `css/base.css` for the required variables and the dark-mode contract.
  Dark mode requires **Quarto >= 1.7**.

## Syncing

Each site repo has Dependabot configured for `gitsubmodule`: when a change
lands here, Dependabot opens a bump PR in each site, whose CI renders the
site before merge. To pull manually:

```bash
git submodule update --remote _common
```
