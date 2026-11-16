// Pure decision logic for the English -> French geo/cookie redirect.
// Kept free of any Cloudflare types so it can run under plain `node --test`.

const ENGLISH_PAGES = ["/", "/cv/", "/learning/", "/apps/", "/contact/"];

// Returns the French twin path for an English page path (with or without a
// trailing slash), or null if pathname is not one of the five English pages.
export function frenchTwin(pathname) {
  for (const page of ENGLISH_PAGES) {
    const noSlash = page.slice(0, -1); // "" for "/"
    if (pathname === page || (noSlash !== "" && pathname === noSlash)) {
      return "/fr" + page;
    }
  }
  return null;
}

// Returns "en" / "fr" for a valid lang cookie, or null for anything else
// (missing, empty, or any other value), so callers treat it as "no cookie".
export function parseLangCookie(cookieHeader) {
  if (!cookieHeader) return null;
  for (const part of cookieHeader.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    const name = part.slice(0, eq).trim();
    if (name !== "lang") continue;
    const value = part.slice(eq + 1).trim();
    return value === "en" || value === "fr" ? value : null;
  }
  return null;
}

const FRENCH_TAGS = new Set(["fr", "fr-fr", "fr-be", "fr-ch"]);

// Returns true when the Accept-Language header's top-priority language
// (highest q, default 1, earliest in the header on a tie) is one of the
// accepted French tags. Malformed entries are skipped without throwing.
export function isFrenchTopLanguage(acceptLanguage) {
  if (!acceptLanguage) return false;
  let bestTag = null;
  let bestQ = -1;
  for (const entry of acceptLanguage.split(",")) {
    const part = entry.trim();
    if (!part) continue;
    const [rawTag, ...params] = part.split(";");
    const tag = rawTag.trim();
    if (!tag) continue;
    let q = 1;
    for (const param of params) {
      const eq = param.indexOf("=");
      if (eq === -1) continue;
      const key = param.slice(0, eq).trim();
      if (key !== "q") continue;
      const value = Number(param.slice(eq + 1).trim());
      if (!Number.isNaN(value)) q = value;
    }
    if (q <= 0) continue;
    if (q > bestQ) {
      bestQ = q;
      bestTag = tag;
    }
  }
  if (bestTag === null) return false;
  return FRENCH_TAGS.has(bestTag.toLowerCase());
}

// Tokens that identify a crawler (search, AI citation/training, social-card
// or Lighthouse) by User-Agent, matched case-insensitively as a substring.
const CRAWLER_TOKENS = [
  "bot",
  "crawler",
  "spider",
  "slurp",
  "googlebot",
  "bingbot",
  "oai-searchbot",
  "chatgpt-user",
  "perplexitybot",
  "claude-searchbot",
  "claude-user",
  "claudebot",
  "gptbot",
  "google-extended",
  "ccbot",
  "applebot",
  "facebookexternalhit",
  "twitterbot",
  "linkedinbot",
  "lighthouse",
  "chrome-lighthouse",
];

// Returns true when the User-Agent header matches a known crawler token.
export function isCrawler(userAgent) {
  if (!userAgent) return false;
  const ua = userAgent.toLowerCase();
  return CRAWLER_TOKENS.some((token) => ua.includes(token));
}

// Returns the French twin path (+ query string) to redirect to, or null to
// serve the English page / fall through unchanged.
export function decideRedirect({
  method,
  pathname,
  search = "",
  cookieHeader = "",
  acceptLanguage = "",
  userAgent = "",
}) {
  if (method !== "GET" && method !== "HEAD") return null;
  const twin = frenchTwin(pathname);
  if (!twin) return null;
  if (isCrawler(userAgent)) return null;
  const lang = parseLangCookie(cookieHeader);
  if (lang === "en") return null;
  if (lang === "fr") return twin + search;
  if (isFrenchTopLanguage(acceptLanguage)) return twin + search;
  return null;
}

// Plain-object response shape for the redirect, so it can be asserted on
// without constructing a real Response.
export function redirectInit(location) {
  return {
    status: 302,
    headers: {
      Location: location,
      "Cache-Control": "private, no-store",
      Vary: "Accept-Language, Cookie",
    },
  };
}

const CANONICAL_HOST = "zakariafadli.com";

// Returns the absolute canonical URL to 301 to when `host` is the www twin
// of the canonical host, or null when it already is the canonical host (or
// anything else, e.g. a *.pages.dev preview, which must not be redirected).
export function decideHostRedirect({ host, pathname, search = "" }) {
  if (host === "www." + CANONICAL_HOST) {
    return "https://" + CANONICAL_HOST + pathname + search;
  }
  return null;
}

// Plain-object response shape for a permanent host canonicalization redirect.
export function hostRedirectInit(location) {
  return {
    status: 301,
    headers: {
      Location: location,
      "Cache-Control": "public, max-age=3600",
    },
  };
}
