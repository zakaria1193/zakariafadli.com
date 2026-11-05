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

// Returns the French twin path (+ query string) to redirect to, or null to
// serve the English page / fall through unchanged.
export function decideRedirect({ method, pathname, search = "", cookieHeader = "", country = "" }) {
  if (method !== "GET" && method !== "HEAD") return null;
  const twin = frenchTwin(pathname);
  if (!twin) return null;
  const lang = parseLangCookie(cookieHeader);
  if (lang === "en") return null;
  if (lang === "fr") return twin + search;
  if (country === "FR") return twin + search;
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
      Vary: "Cookie",
    },
  };
}
