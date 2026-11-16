# Search and AI-search visibility

What was set up for zakariafadli.com to be findable in Google/Bing and
citable by AI answer engines (ticket `zakariafadli-com-0007`), where it was
set up, and how to check each item. Dated 2026-11-16.

## Deploy

Commits `171a7c8` and `5cd13ed` (on-page SEO/structured data, then
sitemap/robots/llms.txt/host canonicalization/geo-redirect crawler
exemption) plus the `www` host-redirect fix below were rebased onto
`origin/main` (which had an unrelated redesign-and-revert in the meantime)
and pushed as `eb95756` + the host-redirect commit. Cloudflare Pages
auto-deploys `site/` on every push to `main` (no build step) — confirmed
live by `curl` within ~90s of the push.

## Classic SEO — live checks

Run on 2026-11-16 against the production domain:

- `curl -s -o /dev/null -w '%{http_code}' https://zakariafadli.com/robots.txt` → 200
- `curl -s -o /dev/null -w '%{http_code}' https://zakariafadli.com/sitemap.xml` → 200
- `curl -s -o /dev/null -w '%{http_code}' https://zakariafadli.com/llms.txt` → 200
- `curl -s -o /dev/null -w '%{http_code}' https://zakariafadli.com/fr/llms.txt` → 200
- `curl -A Googlebot -H 'Accept-Language: fr' -o /dev/null -w '%{http_code}' https://zakariafadli.com/cv/` → 200 (not redirected)
- `curl -o /dev/null -w '%{http_code}' https://zakariafadli.com/` (no cookie, no Accept-Language) → 200
- `curl -I http://zakariafadli.com/` → 301 to `https://...` (Cloudflare "Always Use HTTPS" is on)
- JSON-LD on `/` was read directly from the served HTML: a `@graph` with one `Person`
  (`@id` `.../#person`, `name`, `worksFor.name` "AdaCore", two `alumniOf` entries) and one
  `ProfilePage` whose `mainEntity.@id` matches the Person's `@id`. Structurally valid JSON,
  types and required fields match schema.org's `Person`/`ProfilePage`/`Organization`/
  `CollegeOrUniversity`. **Not independently run through Google's Rich Results Test or
  validator.schema.org** — this run had no connected browser (Claude in Chrome reported
  zero connected browsers), and both tools need one. Re-run manually or via Claude in
  Chrome: paste `https://zakariafadli.com/` and `https://zakariafadli.com/fr/` into
  https://search.google.com/test/rich-results and https://validator.schema.org/.
- Social card: `site/assets/og-card.png`, 1200×630, 248 KB (under the 300 KB budget),
  served at `https://zakariafadli.com/assets/og-card.png` (200).

## Duplicate hosts

- **`*.pages.dev`**: `curl -I https://<project>.pages.dev/` carries
  `x-robots-tag: noindex`. The apex (`curl -I https://zakariafadli.com/`) carries no
  `X-Robots-Tag` header at all — confirmed on both.
- **`www.zakariafadli.com`**: resolves and was serving the site directly (200, not a
  redirect) — it's attached as a Cloudflare Pages custom domain on the same project, so
  there was no DNS/dashboard redirect in front of it to begin with. Fixed in code instead
  of the dashboard (no Claude in Chrome available this run; see Blocked below): added
  `decideHostRedirect()` in `functions/lib/geo-redirect.mjs`, wired into
  `functions/_middleware.js` ahead of the language redirect, 301-ing
  `www.zakariafadli.com/*` to the matching `https://zakariafadli.com/*` (path and query
  kept), leaving `*.pages.dev` alone. Covered by `node --test` cases in
  `functions/lib/geo-redirect.test.mjs`. **Needs a live re-check after this deploys**:
  `curl -I https://www.zakariafadli.com/` should then answer `301` to the apex.
- **`zakaria1193.github.io`** (the old site, ticket `zakariafadli-com-0001`): `curl -I`
  on `/` returns `200` with an HTML `<meta http-equiv="refresh">` redirect to
  `https://zakariafadli.com/` (not a `301`); `/cv` returns a same-host `301` to `/cv/`,
  and `/cv/` itself is the same `200` meta-refresh page (it does not 301 straight to
  zakariafadli.com/cv/). So the old site redirects, but via client-side meta-refresh, not
  an HTTP 301. **Changing the old repo is out of scope for this ticket** (per Spec item
  6); noted here as requested.

## Lighthouse (mobile), 2026-11-16, run via local `lighthouse` CLI

No baseline was captured before the on-page SEO changes (items 1–2, commits `171a7c8`/
`5cd13ed`) landed in earlier runs of this ticket — they were already deployed before this
plan item started, so these are post-deploy numbers only, not a before/after comparison.

| Page | Performance | SEO | Accessibility |
| --- | --- | --- | --- |
| `/` | 98 | 100 | 100 |
| `/cv/` | 100 | 100 | 98 |

Both well clear of the SEO ≥ 95 acceptance bar.

## Blocked this run: account/measurement setup (Spec items 11–12) and the `www` dashboard option

`mcp__claude-in-chrome__list_connected_browsers` returned an empty list — no Chrome
extension was connected in this execution environment, so none of the steps that need a
signed-in browser could run:

- **Google Search Console**: create a Domain property for `zakariafadli.com` (DNS TXT
  verification via Cloudflare DNS), submit `https://zakariafadli.com/sitemap.xml`, run
  URL Inspection + request indexing on `/` and `/fr/`.
- **Bing Webmaster Tools**: import the site from Search Console, confirm/submit the
  sitemap.
- **Cloudflare Web Analytics**: enable via the Pages project's Web Analytics toggle
  (preferred, no code) for `zakariafadli.com`.
- **Rich Results Test / validator.schema.org**: manual run against `/` and `/fr/` (see
  above — the JSON-LD was checked structurally instead).

None of these need a real person for a 2FA/phone step as far as is known yet — they are
blocked purely on browser access, not on Zak specifically. **Next step for Zak (or a
future run with Claude in Chrome connected):**
1. Sign in to Chrome as `zakaria1193` and connect the Claude in Chrome extension.
2. Re-run this ticket's last plan item (or do the four bullets above by hand):
   - search.google.com/search-console → Add property → Domain → `zakariafadli.com` →
     DNS verification → add the given TXT record in the Cloudflare DNS tab for the zone
     → verify → Sitemaps → submit `sitemap.xml` → URL Inspection on `/` and `/fr/` →
     Request indexing.
   - bing.com/webmasters → Import from Google Search Console → confirm the sitemap.
   - Cloudflare dashboard → Pages project → zakariafadli.com → Web Analytics → enable.
   - search.google.com/test/rich-results and validator.schema.org on `/` and `/fr/`.
3. After `www`'s code fix deploys, confirm `curl -I https://www.zakariafadli.com/`
   answers `301` to the apex; if Cloudflare ever detaches `www` from the Pages project
   (so it stops being served by this code), a Cloudflare Redirect Rule in the dashboard
   would be needed instead.

## Training-crawler flag

`site/robots.txt` has one line to flip: in the training-crawler group (GPTBot,
ClaudeBot, Google-Extended, CCBot, Applebot-Extended), change `Allow: /` to
`Disallow: /` to opt out of AI training crawlers. The comment above that line says so.
Search/citation crawlers (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot,
Claude-User, Googlebot, Bingbot) are in separate groups and are unaffected either way —
covered by `scripts/check_site.py`.

## Kill condition

Per the ticket: if, about **6 weeks after the sitemap is accepted** (target check date
once Search Console confirms it — expect to look again around late December 2026 /
early January 2027), Search Console shows almost no impressions for the name query and
there are no AI-engine referrals in Cloudflare Web Analytics, stop further SEO work — a
personal site does not need more.
