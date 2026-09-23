/**
 * Tags input, enhanced: existing tags become removable pills, typing completes
 * from the vocabulary embedded in the page, and the most used tags are one
 * click away.
 *
 * The text input rendered by Django stays the only submitted field: it is
 * hidden and rewritten on every change, so the server keeps parsing the same
 * comma-separated value whether the script ran or not.
 */
(function () {
  "use strict";

  const MAX_SUGGESTIONS = 8;

  /**
   * The name the server would keep: `collect.utils.tags_splitter` drops every
   * other character, so a pill shows what will actually be saved.
   */
  function sanitize(name) {
    return name.replace(/[^0-9a-zA-Z_-]/g, "");
  }

  /**
   * Read a field value the way `tags_splitter` does, on commas and spaces.
   * It also accepts the `#tag, #tag` form `tags_joiner` renders.
   */
  function parseTags(value) {
    return (value || "")
      .split(/[\s,]+/)
      .map(sanitize)
      .filter(Boolean);
  }

  /** The reverse: what the splitter reads back as this exact list. */
  function serializeTags(tags) {
    return tags.join(", ");
  }

  function interpolate(template, tag) {
    return template.replace("%(tag)s", tag);
  }

  function enhance(root) {
    if (root.dataset.enhanced) {
      return;
    }
    const input = root.querySelector('input[type="text"]');
    const payload = root.querySelector('script[type="application/json"]');
    if (!input || !payload) {
      return;
    }
    root.dataset.enhanced = "true";

    const data = JSON.parse(payload.textContent);
    const labels = data.labels;
    let tags = parseTags(input.value);
    let activeIndex = -1;

    // The label rendered by the form points at the input by id: hand that id
    // over to the field the visitor now types in, so clicking it still focuses.
    const inputId = input.id;
    input.type = "hidden";
    input.removeAttribute("id");

    const pills = document.createElement("ul");
    pills.className = "tags-pills";

    const entry = document.createElement("input");
    entry.type = "text";
    entry.className = "tags-entry";
    entry.id = inputId;
    entry.placeholder = labels.placeholder;
    entry.autocomplete = "off";
    entry.setAttribute("role", "combobox");
    entry.setAttribute("aria-autocomplete", "list");
    entry.setAttribute("aria-expanded", "false");
    ["autocapitalize", "autocorrect", "spellcheck"].forEach((name) => {
      if (input.hasAttribute(name)) {
        entry.setAttribute(name, input.getAttribute(name));
      }
    });

    const entryItem = document.createElement("li");
    entryItem.className = "tags-entry-item";
    entryItem.appendChild(entry);

    const suggestions = document.createElement("ul");
    suggestions.className = "tags-suggestions";
    suggestions.id = inputId + "-suggestions";
    suggestions.setAttribute("role", "listbox");
    suggestions.setAttribute("aria-label", labels.suggestions);
    suggestions.hidden = true;
    entry.setAttribute("aria-controls", suggestions.id);

    const chips = document.createElement("div");
    chips.className = "tags-chips";

    const announcer = document.createElement("span");
    announcer.className = "visually-hidden";
    announcer.setAttribute("aria-live", "polite");

    root.append(pills, suggestions, chips, announcer);

    function has(tag) {
      const lowered = tag.toLowerCase();
      return tags.some((existing) => existing.toLowerCase() === lowered);
    }

    function commit() {
      input.value = serializeTags(tags);
      renderPills();
      renderChips();
    }

    function add(text) {
      // Typed text can hold more than one tag, and characters that would not
      // survive the round-trip.
      const added = parseTags(text).filter((name) => {
        if (has(name)) {
          return false;
        }
        tags.push(name);
        return true;
      });
      if (!added.length) {
        return;
      }
      commit();
      announcer.textContent = added
        .map((name) => interpolate(labels.added, name))
        .join(" ");
    }

    function remove(tag) {
      tags = tags.filter((existing) => existing !== tag);
      commit();
      announcer.textContent = interpolate(labels.removed, tag);
    }

    function renderPills() {
      pills.replaceChildren(
        ...tags.map((tag) => {
          const item = document.createElement("li");
          item.className = "tags-pill";
          item.appendChild(document.createTextNode(tag));
          const button = document.createElement("button");
          button.type = "button";
          button.className = "tags-remove";
          button.setAttribute("aria-label", interpolate(labels.remove, tag));
          button.textContent = "×";
          button.addEventListener("click", () => {
            remove(tag);
            entry.focus();
          });
          item.appendChild(button);
          return item;
        }),
        entryItem,
      );
    }

    function renderChips() {
      if (!data.popular.length) {
        return;
      }
      const legend = document.createElement("span");
      legend.className = "tags-chips-label";
      legend.textContent = labels.popular;
      chips.replaceChildren(
        legend,
        ...data.popular.map((tag) => {
          const selected = has(tag);
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "tags-chip";
          chip.textContent = tag;
          // A chip is a toggle, so the same click undoes a mistaken one.
          chip.setAttribute("aria-pressed", selected ? "true" : "false");
          chip.addEventListener("click", () => {
            selected ? remove(tag) : add(tag);
            entry.focus();
          });
          return chip;
        }),
      );
    }

    function closeSuggestions() {
      suggestions.replaceChildren();
      suggestions.hidden = true;
      activeIndex = -1;
      entry.setAttribute("aria-expanded", "false");
      entry.removeAttribute("aria-activedescendant");
    }

    function highlight(index) {
      const options = Array.from(suggestions.children);
      activeIndex = index;
      options.forEach((option, position) => {
        const active = position === index;
        option.classList.toggle("active", active);
        option.setAttribute("aria-selected", active ? "true" : "false");
      });
      if (index < 0) {
        entry.removeAttribute("aria-activedescendant");
      } else {
        entry.setAttribute("aria-activedescendant", options[index].id);
      }
    }

    function renderSuggestions() {
      const keywords = entry.value.trim().toLowerCase();
      if (!keywords) {
        closeSuggestions();
        return;
      }
      // Already usage-ordered by the server, so the first matches are the
      // most used ones.
      const matches = data.vocabulary
        .filter((tag) => tag.toLowerCase().includes(keywords) && !has(tag))
        .slice(0, MAX_SUGGESTIONS);
      if (!matches.length) {
        closeSuggestions();
        return;
      }
      suggestions.replaceChildren(
        ...matches.map((tag, position) => {
          const option = document.createElement("li");
          option.className = "tags-suggestion";
          option.id = suggestions.id + "-" + position;
          option.setAttribute("role", "option");
          option.setAttribute("aria-selected", "false");
          option.textContent = tag;
          // On mousedown, because the click would come after the blur that
          // commits whatever was typed.
          option.addEventListener("mousedown", (event) => {
            event.preventDefault();
            accept(tag);
          });
          return option;
        }),
      );
      suggestions.hidden = false;
      entry.setAttribute("aria-expanded", "true");
      highlight(-1);
    }

    function accept(tag) {
      add(tag);
      entry.value = "";
      closeSuggestions();
      entry.focus();
    }

    entry.addEventListener("input", renderSuggestions);

    entry.addEventListener("keydown", (event) => {
      const options = Array.from(suggestions.children);
      switch (event.key) {
        case "Enter":
        case ",":
          event.preventDefault();
          // The details form saves on Enter from any of its inputs: here it
          // means "this tag is done", nothing more.
          event.stopPropagation();
          accept(
            activeIndex >= 0 ? options[activeIndex].textContent : entry.value,
          );
          break;
        case "Backspace":
          if (!entry.value && tags.length) {
            event.preventDefault();
            remove(tags[tags.length - 1]);
          }
          break;
        case "ArrowDown":
          if (options.length) {
            event.preventDefault();
            highlight((activeIndex + 1) % options.length);
          }
          break;
        case "ArrowUp":
          if (options.length) {
            event.preventDefault();
            highlight((activeIndex <= 0 ? options.length : activeIndex) - 1);
          }
          break;
        case "Escape":
          if (!suggestions.hidden) {
            event.preventDefault();
            event.stopPropagation();
            closeSuggestions();
          }
          break;
      }
    });

    // Enter is also what the details form listens to, on keyup.
    entry.addEventListener("keyup", (event) => {
      if (event.key === "Enter") {
        event.stopPropagation();
      }
    });

    // Leaving the field keeps what was typed, rather than dropping it.
    entry.addEventListener("blur", () => {
      if (entry.value.trim()) {
        add(entry.value);
        entry.value = "";
      }
      closeSuggestions();
    });

    // Same for submitting straight from the tags field, with the button or a
    // keyboard shortcut.
    const form = input.closest("form");
    if (form) {
      form.addEventListener(
        "submit",
        () => {
          if (entry.value.trim()) {
            add(entry.value);
            entry.value = "";
          }
        },
        { capture: true },
      );
    }

    commit();
  }

  function enhanceAll() {
    document.querySelectorAll(".tags-widget").forEach(enhance);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceAll);
  } else {
    enhanceAll();
  }
  // The details page swaps its whole form in on save.
  document.body.addEventListener("htmx:afterSettle", enhanceAll);
})();
