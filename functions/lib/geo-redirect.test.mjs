import { test } from "node:test";
import assert from "node:assert/strict";
import { decideRedirect, redirectInit } from "./geo-redirect.mjs";

test("FR with no cookie redirects", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", country: "FR" }),
    "/fr/"
  );
});

test("FR with lang=en does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", cookieHeader: "lang=en", country: "FR" }),
    null
  );
});

test("non-FR with lang=fr redirects", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/cv/", cookieHeader: "lang=fr", country: "US" }),
    "/fr/cv/"
  );
});

test("non-FR with no cookie does not redirect", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/cv/", country: "US" }),
    null
  );
});

test("a /fr/... path never redirects", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/fr/cv/", cookieHeader: "lang=en", country: "FR" }),
    null
  );
});

test("an asset path never redirects", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/style.css", country: "FR" }),
    null
  );
});

test("a path without a trailing slash maps to the right twin", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/cv", country: "FR" }),
    "/fr/cv/"
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/contact", country: "FR" }),
    "/fr/contact/"
  );
});

test("the query string is kept", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/learning/", search: "?x=1", country: "FR" }),
    "/fr/learning/?x=1"
  );
});

test("an invalid cookie value falls back to geo", () => {
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", cookieHeader: "lang=de", country: "FR" }),
    "/fr/"
  );
  assert.equal(
    decideRedirect({ method: "GET", pathname: "/", cookieHeader: "lang=de", country: "US" }),
    null
  );
});

test("non-GET/HEAD methods never redirect", () => {
  assert.equal(
    decideRedirect({ method: "POST", pathname: "/", country: "FR" }),
    null
  );
});

test("the redirect has 302, Cache-Control private no-store and Vary Cookie", () => {
  const init = redirectInit("/fr/");
  assert.equal(init.status, 302);
  assert.equal(init.headers["Cache-Control"], "private, no-store");
  assert.equal(init.headers["Vary"], "Cookie");
  assert.equal(init.headers["Location"], "/fr/");
});
