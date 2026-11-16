// "Vis på kart": shows an OpenStreetMap map under the event when the button is
// clicked. Nothing is loaded from openstreetmap.org until then. Only one map is
// open at a time: opening one closes the one that was open.
(function () {
  "use strict";
  var buttons = document.querySelectorAll("button.map-btn");

  function close(btn) {
    var panel = document.getElementById(btn.getAttribute("aria-controls"));
    btn.setAttribute("aria-expanded", "false");
    btn.textContent = "Vis på kart";
    if (panel) {
      panel.hidden = true;
      panel.replaceChildren();
    }
  }

  function open(btn) {
    var panel = document.getElementById(btn.getAttribute("aria-controls"));
    if (!panel) return;
    var frame = document.createElement("iframe");
    frame.src = btn.dataset.mapSrc;
    frame.title = "Kart: " + btn.dataset.mapPlace;
    frame.loading = "lazy";
    frame.referrerPolicy = "no-referrer";
    var link = document.createElement("a");
    link.href = btn.dataset.mapLink;
    link.rel = "noopener noreferrer";
    link.target = "_blank";
    link.textContent = "Åpne større kart";
    panel.replaceChildren(frame, link);
    panel.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    btn.textContent = "Skjul kart";
  }

  buttons.forEach(function (btn) {
    btn.hidden = false;  // the button only works with JavaScript, so it starts hidden
    btn.addEventListener("click", function () {
      var wasOpen = btn.getAttribute("aria-expanded") === "true";
      buttons.forEach(function (other) {
        if (other.getAttribute("aria-expanded") === "true") close(other);
      });
      if (!wasOpen) open(btn);
    });
  });
})();
