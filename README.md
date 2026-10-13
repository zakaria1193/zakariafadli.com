# zakariafadli.com

Zakaria Fadli's personal site. Plain HTML, CSS and vanilla JS under `site/`, no build
step and no npm, served by Cloudflare Pages. `functions/` is reserved for Cloudflare
Pages Functions, added later if an API is needed — it holds no function yet.

Replaces the old GitHub Pages site at `zakaria1193.github.io`, moved here for an
Alan-style redesign (deep blue, soft pastels, lots of white space).

## Quick start

```bash
make serve   # http://localhost:8000, site/ as the web root
make test    # stdlib checker: titles, viewport meta, internal links and assets
```

## Page map

Filled in as pages are ported from the old site (next step of this ticket).

| Old page (`zakaria1193.github.io`) | New page |
| --- | --- |
| _pending_ | _pending_ |

## Apps

Filled in once the Apps section is built (a later step of this ticket).

## Secrets

`.env` is git-crypt encrypted, empty for now. Copy `.env.example` to `.env` and
`git-crypt unlock` to use real values once something needs one.

## Cloudflare Pages setup (owner, by hand)

1. In the Cloudflare dashboard, Pages → connect this GitHub repo. Output folder:
   `site`. No build command. It then deploys on every push to `main`.
2. Add `zakariafadli.com` as a custom domain (apex only, plus `www` if wanted —
   `pjm.zakariafadli.com` is a separate subdomain and is not touched by this).
3. Look at the site on its `*.pages.dev` address, check the Apps section's picks,
   then remove `hold` from the go-live ticket (id below once created).

## Follow-up ticket

Go-live ticket id: _pending_ (created by the last step of this ticket).
