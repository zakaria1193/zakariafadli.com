# functions

`_middleware.js` is a Cloudflare Pages Function that runs in front of every
request. On the five English page paths (`/`, `/cv/`, `/learning/`, `/apps/`,
`/contact/`, with or without a trailing slash), it redirects visitors to the
matching `/fr/...` page when:

- their `lang` cookie is `fr`, or
- they have no valid `lang` cookie and the top-priority language in the
  `Accept-Language` request header (highest `q`, default 1, earliest in the
  header on a tie) is `fr`, `fr-FR`, `fr-BE` or `fr-CH`, case-insensitively.

A `lang=en` cookie always keeps the English page. Every other request
(assets, `/fr/...` pages, non-GET/HEAD methods) passes straight through via
`context.next()`. The redirect is a `302` with `Cache-Control: private,
no-store` and `Vary: Accept-Language, Cookie`, and keeps the query string.
Any exception in the function falls through to `context.next()` instead of
erroring.

The decision logic is a pure function in `lib/geo-redirect.mjs`, with no
Cloudflare types, so it is covered by plain `node --test` tests in
`lib/geo-redirect.test.mjs` (run by `make test`, no npm, no dependencies).

`make serve` (a plain `python3 -m http.server`) does not run Pages
Functions, so there is no geo redirect locally; check it on the Cloudflare
Pages preview deployment instead.
