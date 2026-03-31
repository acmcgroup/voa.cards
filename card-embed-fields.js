/**
 * Pré-visualização (embed): aplica texto aos nós [data-card-field] via postMessage do index.
 */
(function () {
  if (!document.documentElement.classList.contains("card-embed")) return;

  function telHref(display) {
    var s = String(display).replace(/\s/g, "").replace(/[()-]/g, "");
    if (!s) return "tel:";
    if (s.slice(0, 1) === "+") return "tel:" + s;
    if (s.slice(0, 2) === "00") return "tel:+" + s.slice(2);
    return "tel:" + s;
  }

  function webHref(display) {
    var u = String(display).trim();
    if (!u) return "https://www.voa.aero";
    if (/^https?:\/\//i.test(u)) return u;
    return "https://" + u.replace(/^\/+/, "");
  }

  function webLabel(display) {
    return String(display)
      .trim()
      .replace(/^https?:\/\//i, "")
      .replace(/\/$/, "");
  }

  function applyFields(fields) {
    if (!fields || typeof fields !== "object") return;
    Object.keys(fields).forEach(function (key) {
      var v = fields[key];
      if (v == null) return;
      v = String(v);
      var sel = "[data-card-field=\"" + key.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + "\"]";
      var els = document.querySelectorAll(sel);
      if (!els.length) return;
      els.forEach(function (el) {
        if (key === "email") {
          el.textContent = v;
          if (el.tagName === "A") {
            el.href = "mailto:" + v.replace(/^mailto:/i, "");
          }
          return;
        }
        if (key === "phone") {
          el.textContent = v;
          if (el.tagName === "A") {
            el.href = telHref(v);
          }
          return;
        }
        if (key === "webUrl") {
          el.textContent = webLabel(v);
          if (el.tagName === "A") {
            el.href = webHref(v);
          }
          return;
        }
        el.textContent = v;
      });
    });
  }

  window.addEventListener("message", function (ev) {
    var d = ev.data;
    if (!d || d.source !== "voa-card-shell") return;
    if (d.type === "fields-update") {
      applyFields(d.fields);
    }
  });
})();
