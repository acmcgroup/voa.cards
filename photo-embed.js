/**
 * Pré-visualização (embed): foto na moldura com arrastar, zoom com scroll e reset via mensagens do index.
 * Só corre com class "card-embed" no <html>.
 */
(function () {
  if (!document.documentElement.classList.contains("card-embed")) return;

  var wrap = document.querySelector(".photo-wrap");
  if (!wrap) return;

  var viewport = wrap.querySelector(".photo-viewport");
  var img = wrap.querySelector(".photo-user-img");
  if (!viewport || !img) return;

  var state = { panX: 0, panY: 0, zoom: 1 };
  var layoutKey = "unknown";
  var dragging = false;
  var lastX = 0;
  var lastY = 0;
  var wheelTimer = null;

  function applyTransform() {
    img.style.transform =
      "translate(-50%, -50%) translate(" +
      state.panX +
      "px," +
      state.panY +
      "px) scale(" +
      state.zoom +
      ")";
  }

  function computeCoverScale() {
    var rect = viewport.getBoundingClientRect();
    var nw = img.naturalWidth;
    var nh = img.naturalHeight;
    if (!nw || !nh || rect.width < 1 || rect.height < 1) return;
    var coverScale = Math.max(rect.width / nw, rect.height / nh);
    img.style.width = nw * coverScale + "px";
    img.style.height = "auto";
  }

  function notifyParent() {
    if (window.parent === window) return;
    try {
      window.parent.postMessage(
        {
          source: "voa-card-preview",
          type: "photo-update",
          layoutKey: layoutKey,
          panX: state.panX,
          panY: state.panY,
          zoom: state.zoom,
        },
        "*"
      );
    } catch (e) {}
  }

  function scheduleNotifyParent() {
    if (wheelTimer) clearTimeout(wheelTimer);
    wheelTimer = setTimeout(function () {
      wheelTimer = null;
      notifyParent();
    }, 120);
  }

  function refreshAfterImageGeometry() {
    computeCoverScale();
    applyTransform();
  }

  function setImageFromDataUrl(dataUrl) {
    if (!dataUrl) {
      wrap.classList.remove("card-embed--has-photo");
      img.removeAttribute("src");
      state.panX = 0;
      state.panY = 0;
      state.zoom = 1;
      return;
    }
    wrap.classList.add("card-embed--has-photo");
    img.onload = function () {
      img.onload = null;
      refreshAfterImageGeometry();
    };
    img.src = dataUrl;
    if (img.complete && img.naturalWidth) {
      img.onload = null;
      refreshAfterImageGeometry();
    }
  }

  function resetView() {
    state.panX = 0;
    state.panY = 0;
    state.zoom = 1;
    if (img.src) {
      refreshAfterImageGeometry();
    }
    notifyParent();
  }

  function onPointerDown(e) {
    if (!wrap.classList.contains("card-embed--has-photo")) return;
    if (e.button !== undefined && e.button !== 0) return;
    e.preventDefault();
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    img.classList.add("is-dragging");
    try {
      viewport.setPointerCapture(e.pointerId);
    } catch (err) {}
  }

  function onPointerMove(e) {
    if (!dragging) return;
    state.panX += e.clientX - lastX;
    state.panY += e.clientY - lastY;
    lastX = e.clientX;
    lastY = e.clientY;
    applyTransform();
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;
    img.classList.remove("is-dragging");
    notifyParent();
  }

  function onWheel(e) {
    if (!wrap.classList.contains("card-embed--has-photo")) return;
    e.preventDefault();
    var factor = Math.exp(-e.deltaY * 0.0012);
    state.zoom = Math.min(4, Math.max(0.35, state.zoom * factor));
    applyTransform();
    scheduleNotifyParent();
  }

  viewport.addEventListener("pointerdown", onPointerDown);
  viewport.addEventListener("pointermove", onPointerMove);
  viewport.addEventListener("pointerup", endDrag);
  viewport.addEventListener("pointercancel", endDrag);
  viewport.addEventListener("lostpointercapture", endDrag);
  viewport.addEventListener("wheel", onWheel, { passive: false });

  window.addEventListener("resize", function () {
    if (wrap.classList.contains("card-embed--has-photo")) {
      refreshAfterImageGeometry();
    }
  });

  window.addEventListener("message", function (ev) {
    var d = ev.data;
    if (!d || d.source !== "voa-card-shell") return;

    if (d.type === "photo-init") {
      layoutKey = d.layoutKey || "unknown";
      if (d.panX != null) state.panX = d.panX;
      if (d.panY != null) state.panY = d.panY;
      if (d.zoom != null) state.zoom = d.zoom;
      if (d.imageDataUrl) {
        setImageFromDataUrl(d.imageDataUrl);
      } else {
        setImageFromDataUrl(null);
      }
    }

    if (d.type === "photo-reset") {
      resetView();
    }
  });
})();

