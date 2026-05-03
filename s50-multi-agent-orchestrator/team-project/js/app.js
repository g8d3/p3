(() => {
  "use strict";

  const STORAGE_KEY = "todos";

  const load = () => JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  const save = (todos) => localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));

  let todos = load();
  let filter = "all"; // "all" | "active" | "completed"

  // DOM refs
  const form = document.getElementById("todo-form");
  const input = document.getElementById("todo-input");
  const list = document.getElementById("todo-list");
  const countEl = document.getElementById("todo-count");
  const filtersEl = document.getElementById("filters");
  const clearBtn = document.getElementById("clear-completed");

  // --- Rendering ---

  function filtered() {
    if (filter === "active") return todos.filter((t) => !t.completed);
    if (filter === "completed") return todos.filter((t) => t.completed);
    return todos;
  }

  function render() {
    list.innerHTML = "";
    for (const todo of filtered()) {
      const li = document.createElement("li");
      li.dataset.id = todo.id;
      if (todo.completed) li.classList.add("completed");

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = todo.completed;
      cb.addEventListener("change", () => toggle(todo.id));

      const span = document.createElement("span");
      span.className = "todo-text";
      span.textContent = todo.text;

      const del = document.createElement("button");
      del.className = "delete-btn";
      del.textContent = "\u00d7";
      del.addEventListener("click", () => remove(todo.id));

      li.append(cb, span, del);
      list.appendChild(li);
    }

    const active = todos.filter((t) => !t.completed).length;
    countEl.textContent = `${active} item${active !== 1 ? "s" : ""} left`;

    filtersEl.querySelectorAll("button").forEach((btn) => {
      btn.classList.toggle("selected", btn.dataset.filter === filter);
    });

    clearBtn.style.display = todos.some((t) => t.completed) ? "" : "none";
  }

  // --- Actions ---

  function add(text) {
    todos.push({ id: Date.now().toString(), text, completed: false });
    save(todos);
    render();
  }

  function toggle(id) {
    const todo = todos.find((t) => t.id === id);
    if (todo) {
      todo.completed = !todo.completed;
      save(todos);
      render();
    }
  }

  function remove(id) {
    todos = todos.filter((t) => t.id !== id);
    save(todos);
    render();
  }

  function clearCompleted() {
    todos = todos.filter((t) => !t.completed);
    save(todos);
    render();
  }

  function setFilter(f) {
    filter = f;
    render();
  }

  // --- Event wiring ---

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (text) {
      add(text);
      input.value = "";
    }
  });

  filtersEl.addEventListener("click", (e) => {
    if (e.target.dataset.filter) setFilter(e.target.dataset.filter);
  });

  clearBtn.addEventListener("click", clearCompleted);

  render();
})();
