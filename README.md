# zakariafadli.com

Zakaria Fadli's personal site. Plain HTML, CSS and vanilla JS under `site/`, no build
step and no npm, served by Cloudflare Pages. `functions/` is reserved for Cloudflare
Pages Functions, added later if an API is needed — it holds no function yet.

Replaces the old GitHub Pages site at `zakaria1193.github.io`, moved here for an
Alan-style redesign (deep blue, soft pastels, lots of white space).

## Quick start

```bash
make serve   # http://localhost:8000, site/ as the web root
make test    # stdlib checker: titles, viewport meta, internal links/assets and every
             # external link (needs the network)
```

## Page map

The old site was a React app (create-react-app + react-router); its real routes were
`/`, `/cv` and `/learning` (a hidden homepage grid also linked `/resume`, `/blog` and
`/resources`, but those routes were never registered in `src/index.js` and rendered
nothing live, so they have no new page). Every route that was live is ported, same path:

| Old page (`zakaria1193.github.io`) | New page |
| --- | --- |
| `/` (Home: intro banner + photo) | `/` |
| `/cv` (CV: Experience + Education) | `/cv/` |
| `/learning` (Embedded Learning Resources) | `/learning/` |
| _(new, not on the old site)_ | `/apps/` |

Assets copied word for word: `public/photo.jpg` → `site/assets/photo.jpg`,
`src/assets/enseeiht_logo.png` → `site/assets/enseeiht-logo.png`,
`src/assets/georgia_tech_extended_logo.png` → `site/assets/georgia-tech-logo.png`,
`src/assets/netatmo_logo.png` → `site/assets/netatmo-logo.png`. The old site has no CV
PDF, so none is copied. `site/assets/legrand-logo.svg` is not from the old site: it's
the official Legrand logo, downloaded from Wikimedia Commons at
https://upload.wikimedia.org/wikipedia/commons/7/73/Logo_Legrand_SA.svg.

## Apps

`/apps/` shows computerrev first, then aicli, then 3 public repos, picked from
`gh repo list zakaria1193 --visibility public` by actually having AI involved in building
them (a Claude/Copilot/GPT commit trail, not just the phrase "AI" in a README), being
non-empty, non-fork and having a README. **Owner: please check these before removing
`hold` from the go-live ticket** — swap any of them out if they're not the ones you'd
want on the front page.

| Pick | Why |
| --- | --- |
| **computerrev** (`computerrevision`, private) | An interactive AArch64/RISC-V/x86/Cortex-M exception-handling reference, built with Claude (has a `CLAUDE.md`). Deployed publicly to Cloudflare Pages at `https://computerrevision.pages.dev` (the source repository remains private). |
| **aicli** | A proxy for AI coding CLIs: routes Zak's scripts through Claude Code / Antigravity subscriptions (far cheaper than API pricing) with one switchable routing table, usage log and an OpenAI-compatible endpoint. More backends planned. Pulled out of homelab into its own public repo on 2026-10-21 and added at the owner's request. |
| **gdb2dict** | A small debugging tool with a real audience: published on PyPI, with passing CI and a merged PR with a `Co-Authored-By: Claude` trailer. The clearest "AI helped ship something people actually use" pick. |
| **mockerbee** | A C++ Zigbee device-mocking library where several merged PRs came from an autonomous GPT PR bot (`ci: Add name to gpt workflow`) rather than a human — the most literal "AI wrote this" example, even though the library itself is still marked a draft in its own README. |

Repos considered and left out: `autotools_installer`, `emb-linux-common`,
`my_cpp_boilerplate`, `sniffertunnel`, `zap-gatsby` (no AI commit trail found —
hand-written), `can-you-review` (no README), `bustimes` (empty repo), and all forks
(`arr-mcp`, `kandev`, `kandev-plugin-slack`, `LazyVim`, etc., excluded by the spec).

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

Go-live ticket id: `zakariafadli-com-0001`.
