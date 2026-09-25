/*
 * Generic, dependency-free "saved queries" module for offline "Map-in-a-
 * Box" reports: keeps a named list of caller-defined filter-state objects
 * in browser localStorage (scoped per report via a caller-supplied key),
 * with JSON export/import to move or back up saved queries outside the
 * browser.
 *
 * Schema-free extraction of a pattern used in an offline case study of the
 * Spatial Report Crafter method (see
 * docs/lessons_learned_offline_case_study.md). Contains no project data,
 * field names, or schema — the shape of the saved "filter state" object is
 * entirely up to the caller.
 *
 * Usage:
 *   import { createSavedQueries } from "./saved_queries.js";
 *   const savedQueries = createSavedQueries({
 *     storageKey: "myReport:savedQueries",
 *     // Capture whatever filter/query state your report needs to restore.
 *     captureState: () => ({
 *       category: categoryFilter.value,
 *       query: queryInput.value,
 *     }),
 *     applyState: (state) => {
 *       categoryFilter.value = state.category || "";
 *       queryInput.value = state.query || "";
 *       runQuery();
 *     },
 *   });
 *   saveButton.addEventListener("click", () => savedQueries.save(nameInput.value));
 *   selectEl.addEventListener("change", () => savedQueries.load(selectEl.value));
 */

export function createSavedQueries({ storageKey, captureState, applyState, onListChanged }) {
  function loadList() {
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function persistList(list) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(list));
    } catch (err) {
      throw new Error(`Could not save to browser storage: ${err.message}`);
    }
    if (typeof onListChanged === "function") onListChanged(list);
  }

  function save(name) {
    const trimmedName = (name || "").trim();
    if (!trimmedName) throw new Error("Enter a name for this saved query.");
    const list = loadList().filter((entry) => entry.name !== trimmedName);
    list.push({ name: trimmedName, state: captureState() });
    persistList(list);
    return list;
  }

  function load(name) {
    const entry = loadList().find((item) => item.name === name);
    if (!entry) return false;
    applyState(entry.state || {});
    return true;
  }

  function remove(name) {
    persistList(loadList().filter((entry) => entry.name !== name));
  }

  function exportAll() {
    const list = loadList();
    if (!list.length) throw new Error("No saved queries to export yet.");
    return JSON.stringify(list, null, 2);
  }

  function importFromJson(jsonText) {
    const imported = JSON.parse(jsonText);
    if (!Array.isArray(imported)) throw new Error("file does not contain a JSON array of saved queries");
    const existing = loadList();
    const byName = new Map(existing.map((entry) => [entry.name, entry]));
    for (const entry of imported) {
      if (entry && entry.name) byName.set(entry.name, entry);
    }
    persistList([...byName.values()]);
    return imported.length;
  }

  return { loadList, save, load, remove, exportAll, importFromJson };
}

/** Small helper for wiring an `<input type="file">` import control up to
 * `importFromJson`, e.g.:
 *   fileInput.addEventListener("change", (event) => readImportedFile(event, savedQueries.importFromJson));
 */
export function readImportedFile(changeEvent, onJsonText) {
  const file = changeEvent.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      onJsonText(reader.result);
    } finally {
      changeEvent.target.value = "";
    }
  };
  reader.readAsText(file);
}
