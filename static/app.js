// static/app.js

function getPreference(key, defaultValue) {
  var stored = localStorage.getItem(key);
  return stored !== null ? stored : defaultValue;
}

function setPreference(key, value) {
  localStorage.setItem(key, value);
}

function applyCollapseState(selector, preferenceKey) {
  var state = getPreference(preferenceKey, "collapsed");
  document.querySelectorAll(selector).forEach(function(el) {
    el.open = state === "expanded";
  });
}

function toggleAll(selector, preferenceKey, button) {
  var current = getPreference(preferenceKey, "collapsed");
  var next = current === "collapsed" ? "expanded" : "collapsed";
  setPreference(preferenceKey, next);
  document.querySelectorAll(selector).forEach(function(el) {
    el.open = next === "expanded";
  });
  button.textContent = button.dataset.label + ": " + next;
}

function setActiveToggle(clickedButton) {
  var buttons = clickedButton.parentElement.querySelectorAll("button");
  buttons.forEach(function(b) { b.classList.remove("active"); });
  clickedButton.classList.add("active");
}

function applyContentMode() {
  var mode = getPreference("content-mode", "markdown");
  document.querySelectorAll(".text-block-md").forEach(function(el) {
    el.style.display = mode === "markdown" ? "" : "none";
  });
  document.querySelectorAll(".text-block-raw").forEach(function(el) {
    el.style.display = mode === "raw" ? "" : "none";
  });
}

function toggleContentMode(button) {
  var current = getPreference("content-mode", "markdown");
  var next = current === "markdown" ? "raw" : "markdown";
  setPreference("content-mode", next);
  applyContentMode();
  button.textContent = "Content: " + next;
}

document.addEventListener("DOMContentLoaded", function() {
  applyCollapseState(".collapsible-thinking", "thinking-state");
  applyCollapseState(".collapsible-tool", "tool-state");
  applyContentMode();

  var thinkingBtn = document.getElementById("toggle-thinking");
  if (thinkingBtn) {
    thinkingBtn.textContent = "Thinking: " + getPreference("thinking-state", "collapsed");
  }
  var toolBtn = document.getElementById("toggle-tools");
  if (toolBtn) {
    toolBtn.textContent = "Tool calls: " + getPreference("tool-state", "collapsed");
  }
  var contentBtn = document.getElementById("toggle-content");
  if (contentBtn) {
    contentBtn.textContent = "Content: " + getPreference("content-mode", "markdown");
  }

  // Scroll to message if URL has a hash
  if (window.location.hash) {
    var target = document.querySelector(window.location.hash);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("highlight-flash");
    }
  }
});

document.addEventListener("htmx:afterSwap", function() {
  applyCollapseState(".collapsible-thinking", "thinking-state");
  applyCollapseState(".collapsible-tool", "tool-state");
  applyContentMode();
});
