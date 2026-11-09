import { test } from "node:test";
import assert from "node:assert/strict";
import { decideRedirect, redirectInit } from "./geo-redirect.mjs";

for (const tag of ["fr", "fr-FR", "fr-BE", "fr-CH"]) {
  test(`${tag} as top language redirects`, () => {
    assert.equal(
      decideRedirect({ method: "GET", pathname: "/", acceptLanguage: tag }),
      "/fr/"
    );
  });
}

test("the match is case-insensitive", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "FR-fr" }),
    "/fr/"
  );
});

test("q value decides priority, not header position", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      acceptLanguage: "en;q=0.5, fr;q=0.9",
    }),
    "/fr/"
  );
});

test("a tie in q is broken by earliest position", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      acceptLanguage: "en;q=0.8, fr;q=0.8",
    }),
    null
  );
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      acceptLanguage: "fr;q=0.8, en;q=0.8",
    }),
    "/fr/"
  );
});

test("fr-CA on top does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "fr-CA, fr;q=0.9" }),
    null
  );
});

test("en on top with fr second does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "en-US, fr;q=0.9" }),
    null
  );
});

test("fr;q=0 is not a choice of French", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "fr;q=0" }),
    null
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "fr;q=0, en;q=0.5" }),
    null
  );
});

test("a bare * never counts as French", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "*" }),
    null
  );
});

test("a missing Accept-Language header does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/" }),
    null
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: "" }),
    null
  );
});

test("a malformed header is skipped without throwing", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: ",;q=, fr" }),
    "/fr/"
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", acceptLanguage: ";;;" }),
    null
  );
});

test("lang=en always wins over the header", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      cookieHeader: "lang=en",
      acceptLanguage: "fr-FR",
    }),
    null
  );
});

test("lang=fr always wins over the header", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/cv/",
      cookieHeader: "lang=fr",
      acceptLanguage: "en-US",
    }),
    "/fr/cv/"
  );
});

test("an invalid cookie value falls back to the header", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      cookieHeader: "lang=de",
      acceptLanguage: "fr-FR",
    }),
    "/fr/"
  );
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/",
      cookieHeader: "lang=de",
      acceptLanguage: "en-US",
    }),
    null
  );
});

test("non-FR header with no cookie does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/cv/", acceptLanguage: "en-US" }),
    null
  );
});

test("a /fr/... path never redirects", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/fr/cv/",
      cookieHeader: "lang=en",
      acceptLanguage: "fr-FR",
    }),
    null
  );
});

test("an asset path never redirects", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/style.css", acceptLanguage: "fr-FR" }),
    null
  );
});

test("a path without a trailing slash maps to the right twin", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/cv", acceptLanguage: "fr-FR" }),
    "/fr/cv/"
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/contact", acceptLanguage: "fr-FR" }),
    "/fr/contact/"
  );
});

test("the query string is kept", () => {
  assert.equal(
    decideRedirect({
      method: "GET",
      pathname: "/learning/",
      search: "?x=1",
      acceptLanguage: "fr-FR",
    }),
    "/fr/learning/?x=1"
  );
});

test("non-GET/HEAD methods never redirect", () => {
  assert.equal(
    decideRedirect({ method: "POST", pathname: "/", acceptLanguage: "fr-FR" }),
    null
  );
});

test("the redirect has 302, Cache-Control private no-store and the new Vary", () => {
  const init = redirectInit("/fr/");
  assert.equal(init.status, 302);
  assert.equal(init.headers["Cache-Control"], "private, no-store");
  assert.equal(init.headers["Vary"], "Accept-Language, Cookie");
  assert.equal(init.headers["Location"], "/fr/");
});
