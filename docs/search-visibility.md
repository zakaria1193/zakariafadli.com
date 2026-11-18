# Search and AI-search visibility

What was set up for zakariafadli.com to be findable in Google/Bing and
citable by AI answer engines (ticket `zakariafadli-com-0007`), where it was
set up, and how to check each item. Dated 2026-11-16, updated 2026-11-18
once Claude in Chrome was connected and the account setup could be finished.

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
- **Google Rich Results Test** (search.google.com/test/rich-results), run live against
  both home pages on 2026-11-18: `https://zakariafadli.com/` → "1 valid item detected"
  (ProfilePage), crawled successfully, no errors. `https://zakariafadli.com/fr/` → same
  result. Account used: Search Console-linked Google account signed in to Chrome.
- **Schema.org validator** (validator.schema.org), same two URLs, same date: both report
  the `ProfilePage` entity with `0 ERRORS 0 WARNINGS`, and the nested `Person` (with
  `worksFor`, both `alumniOf` entries, `address`) parses correctly with the same 0/0
  count. FR page correctly shows `inLanguage: "fr"` and the translated `jobTitle`/
  `knowsAbout` values.
- Social card: `site/assets/og-card.png`, 1200×630, 248 KB (under the 300 KB budget),
  served at `https://zakariafadli.com/assets/og-card.png` (200).

## Duplicate hosts

- **`*.pages.dev`**: `curl -I https://<project>.pages.dev/` carries
  `x-robots-tag: noindex`. The apex (`curl -I https://zakariafadli.com/`) carries no
  `X-Robots-Tag` header at all — confirmed on both.
- **`www.zakariafadli.com`**: resolves and was serving the site directly (200, not a
  redirect) — it's attached as a Cloudflare Pages custom domain on the same project, so
  there was no DNS/dashboard redirect in front of it to begin with. Fixed in code instead
  of the dashboard (confirmed as the right call once Claude in Chrome connected — see
  "`www` host redirect" below): added `decideHostRedirect()` in
  `functions/lib/geo-redirect.mjs`, wired into
  `functions/_middleware.js` ahead of the language redirect, 301-ing
  `www.zakariafadli.com/*` to the matching `https://zakariafadli.com/*` (path and query
  kept), leaving `*.pages.dev` alone. Covered by `node --test` cases in
  `functions/lib/geo-redirect.test.mjs`. Confirmed live after deploy (commit `0eacbc2`):
  `curl -I https://www.zakariafadli.com/` now answers `301` to `https://zakariafadli.com/`,
  and the French geo-redirect for real browsers is unaffected (a normal UA with
  `Accept-Language: fr` on `/` still gets a `302` to `/fr/`).
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

`make test` (`node --test`, 40/40) and `scripts/check_site.py`'s structural checks
(titles, canonical, OG/Twitter, h1/alt, JSON-LD, sitemap, robots.txt, `llms.txt`,
`_headers`) all pass as of 2026-11-18, including the new Web Analytics beacon's URL in
the external-link check. The *only* failure seen was the pre-existing `velux.com` /
`velux.co.uk/active` links on `cv/index.html` and `fr/cv/index.html` (unrelated to this
plan item, predates it — see `git log -- site/cv/index.html`) returning `503` from
velux.com's own server at the time of the run; re-checked directly with `curl`
independent of the test script and it was still `503`. If this persists, it's worth a
look in a future ticket, but it's outside this one's scope.

## Account and measurement setup (Spec items 11–12), done 2026-11-18

Done once Claude in Chrome connected to a signed-in browser (zakaria1193). The earlier
run's "Blocked" note (no connected browser) is resolved; details kept here for history.

- **Google Search Console**: created a **Domain property** for `zakariafadli.com`.
  Verification offered an OAuth "authorize Google to manage DNS on Cloudflare" shortcut —
  declined that (broader access than the ticket asked for) and used the manual **DNS TXT
  record** method instead: Search Console gave
  `google-site-verification=zfrJeD258U1vELxfcDHNVJlowxz4w9v6LHknDh4x9mA`, added as a new
  `TXT` record at `@` in the Cloudflare DNS zone (no existing records touched), verified
  instantly. Submitted `https://zakariafadli.com/sitemap.xml` (accepted). Ran URL
  Inspection and **requested indexing** on both `https://zakariafadli.com/` and
  `https://zakariafadli.com/fr/` (both already showed "URL is on Google" from the old
  site at this address; indexing was requested anyway so Google re-crawls the new
  content/structured data). Check: search.google.com/search-console, property
  `zakariafadli.com` (Domain), Sitemaps and URL Inspection tabs.
- **Bing Webmaster Tools**: used "Import from Google Search Console" (the ticket's
  preferred method) — this asks for a Google OAuth grant scoped to
  `webmasters.readonly` (view-only), separate from and narrower than the Cloudflare DNS
  grant declined above; matches what the ticket's Spec item 11 asks for, so it was
  accepted. Imported `https://zakariafadli.com/` (1 site found, 1 imported). Bing's
  import did not carry over a sitemap (0 sitemaps shown), so submitted
  `https://zakariafadli.com/sitemap.xml` manually from the Sitemaps page — accepted,
  status "Processing". Check: bing.com/webmasters, site `zakariafadli.com`, Sitemaps tab.
- **Cloudflare Web Analytics**: the Pages project (`zakariafadli-com`) has no built-in
  Web Analytics toggle in the current dashboard UI (checked Deployments/Metrics/Settings
  tabs — none). Used the account-level Web Analytics page instead
  (dash.cloudflare.com → Analytics → Web analytics → Add a site): entering
  `zakariafadli.com` reported "does not belong to any website on your Cloudflare
  account" even though the zone itself is on Cloudflare (the automatic/zone-proxied mode
  only offers zones with no existing analytics some other way — not reproduced further),
  so it fell back to the **JS snippet** method, same as the spec's documented fallback.
  Snippet (public token, safe to commit):
  ```html
  <script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token": "bb8e69991fa24a0f8a4fbbac76fc7baa"}'></script>
  ```
  Added to all 10 pages under `site/`, right after the existing `<script src="/lang.js">`
  line and before `</body>`. `make test`'s external-link check resolves
  `static.cloudflareinsights.com` fine (no error reported for it). Check:
  dash.cloudflare.com → Web analytics → `zakariafadli.com`, once there is live traffic.
- **Rich Results Test / Schema.org validator**: done, see above — both pass clean.

## `www` host redirect

`www.zakariafadli.com` is a Cloudflare Pages custom domain on the same project as the
apex (confirmed in the Pages project's Deployments tab: "Domains: www.zakariafadli.com,
zakariafadli.com, zakariafadli-com.pages.dev"), so the code-level fix (`_middleware.js`
host check, see above) is the right mechanism, not a dashboard Redirect Rule — confirmed
live: `curl -I https://www.zakariafadli.com/` answers `301` to the apex, path and query
kept, with no regression to the French geo-redirect.

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
