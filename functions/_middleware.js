import {
  decideRedirect,
  redirectInit,
  decideHostRedirect,
  hostRedirectInit,
} from "./lib/geo-redirect.mjs";

export async function onRequest(context) {
  try {
    const { request } = context;
    const url = new URL(request.url);
    const hostTarget = decideHostRedirect({
      host: url.hostname,
      pathname: url.pathname,
      search: url.search,
    });
    if (hostTarget) {
      return new Response(null, hostRedirectInit(hostTarget));
    }
    const target = decideRedirect({
      method: request.method,
      pathname: url.pathname,
      search: url.search,
      cookieHeader: request.headers.get("Cookie") || "",
      acceptLanguage: request.headers.get("Accept-Language") || "",
      userAgent: request.headers.get("User-Agent") || "",
    });
    if (target) {
      return new Response(null, redirectInit(target));
    }
  } catch (err) {
    // Any failure here must never break the site: fall through to the
    // English page instead of surfacing an error.
  }
  return context.next();
}
