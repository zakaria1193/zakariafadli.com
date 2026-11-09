// Saves the visitor's manual EN/FR choice so it beats the Accept-Language redirect next time.
(function () {
  function setLangCookie(value) {
    var secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie =
      "lang=" + value + "; Path=/; Max-Age=31536000; SameSite=Lax" + secure;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var links = document.querySelectorAll(".lang-toggle a[data-lang]");
    links.forEach(function (link) {
      link.addEventListener("click", function () {
        setLangCookie(link.getAttribute("data-lang"));
      });
    });
  });
})();
