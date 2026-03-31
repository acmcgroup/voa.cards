(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var bar = document.querySelector(".card-export-bar");
    if (!bar) return;
    var btn = bar.querySelector(".card-export-print");
    if (btn) {
      btn.addEventListener("click", function () {
        window.print();
      });
    }
  });
})();
