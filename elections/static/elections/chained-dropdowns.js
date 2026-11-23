/*
 * Chained dropdowns (LGA -> Ward -> Polling unit).
 *
 * How it works:
 *  - A <select> that has  data-target="#other"  is a "parent". When its value
 *    changes we call its  data-url  (a small JSON endpoint) with
 *    ?<data-param>=<value>  and fill the #other <select> with the answer.
 *  - Filling a child fires a "change" event on it, so the chain continues
 *    (LGA -> Ward -> Polling unit) without any extra code.
 *  - The child's  data-selected  holds the value to pre-select once its options
 *    have loaded (used when the page is re-displayed with results or errors).
 */
(function () {
  "use strict";

  // Replace the options of `select` with a placeholder plus the given items.
  function setOptions(select, placeholder, items) {
    select.innerHTML = "";
    select.add(new Option(placeholder, ""));
    items.forEach(function (item) {
      select.add(new Option(item.name, item.id));
    });
  }

  // Load the child dropdown of `parent` from its JSON endpoint.
  function loadChild(parent) {
    var child = document.querySelector(parent.dataset.target);
    var placeholder = child.dataset.placeholder || "-- Select --";

    // Nothing chosen in the parent: reset the child (and, via "change", its children).
    if (!parent.value) {
      setOptions(child, "-- Select above first --", []);
      child.disabled = true;
      child.dispatchEvent(new Event("change"));
      return;
    }

    setOptions(child, "Loading...", []);
    child.disabled = true;

    var url = parent.dataset.url + "?" + parent.dataset.param + "=" + encodeURIComponent(parent.value);
    fetch(url)
      .then(function (response) {
        if (!response.ok) { throw new Error("HTTP " + response.status); }
        return response.json();
      })
      .then(function (items) {
        if (items.length === 0) {
          setOptions(child, "No options available", []);
          child.disabled = true;
        } else {
          setOptions(child, placeholder, items);
          child.disabled = false;
          // Restore the earlier choice (once) if the server told us which one.
          if (child.dataset.selected) {
            child.value = child.dataset.selected;
            child.dataset.selected = "";
          }
        }
        child.dispatchEvent(new Event("change"));   // continue down the chain
      })
      .catch(function () {
        setOptions(child, "Could not load - please retry", []);
        child.disabled = true;
      });
  }

  // Wire up every parent <select>; if it already has a value, load its child now.
  document.querySelectorAll("select[data-target]").forEach(function (parent) {
    parent.addEventListener("change", function () { loadChild(parent); });
    if (parent.value) { loadChild(parent); }
  });
})();
