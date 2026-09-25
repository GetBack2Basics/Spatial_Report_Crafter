# Lessons learned: an offline, no-cloud "Map-in-a-Box" case study

This note documents patterns discovered while applying the Spatial Report
Crafter method to a small set of standalone spatial review reports built
entirely offline — no Wherobots/Apache Sedona cluster, no cloud spatial
engine, no web server, and no paid GIS licences. It generalises the
techniques only; no project data, field names, or schema are reproduced
here (see `scripts/offline_toolkit/` for the accompanying schema-free code).

The reports in that case study were regenerated from source Excel workbooks
and a File Geodatabase, each with its own small Python builder script, and
opened directly from disk (`file://`) in a browser — no `npm install`, no
server, no account/API key required by the end user.

## Why this matters: an "Option B" architecture

The main README describes a cloud config-driven pipeline
(`build_config_report.py` + `configs/*.json` + `templates/*.html`) backed
by Wherobots Cloud / Apache Sedona. That's the right choice when:

- Datasets are large enough, or update often enough, that repeated heavy
  spatial SQL (buffers, `ST_Difference`, network routing) benefits from a
  managed spatial engine, and
- A team already has cloud spatial infrastructure and wants many report
  variants driven from one shared template.

**Option B — a fully offline, per-dataset generator** is a better fit when:

- There is no cloud spatial engine available (a desktop GIS install and a
  handful of Excel/GeoPackage/File Geodatabase sources are all that's on
  hand), and/or
- Each dataset's report is different enough (its own filters, its own
  domain-specific summary section) that a single shared config schema
  would add more indirection than it saves, and/or
- The reports must be distributable as a handful of self-contained files
  with **zero** ongoing compute cost and no dependency on an internet
  connection to function (only the basemap tiles need connectivity).

In Option B, each report is its own small, self-contained Python script
(`build_<dataset>_report.py`) that reads a source workbook/geodatabase,
cleans/validates it in memory (never mutating the source file), and emits
an HTML file plus a companion data file plus companion GeoJSON. There is no
shared JSON config or shared HTML template — the report's HTML/CSS/JS is
generated directly by the script, with only truly cross-cutting concerns
(see below) factored into small shared helper modules. This trades some
duplication between report scripts for much lower ceremony per dataset.

Neither option is "better" in general — they answer different constraints.
It's worth documenting Option B explicitly so future adopters of this
method who don't have a cloud spatial engine available don't have to
rediscover these patterns from scratch.

## Lessons learned

### 1. `fetch()`/XHR of local files is unreliable — use `<script src>` instead
Chromium-based browsers commonly block `fetch()`/`XMLHttpRequest` reads of
`file://` URLs (CORS), which breaks the "just open the HTML file, no server"
promise the moment the payload is externalised as a `.json` file. A classic
`<script src="report_data.js">` tag that assigns `window.REPORT_DATA = {...}`
has no such restriction and works identically whether the report is opened
from disk or served over HTTP — so it's the portable choice for keeping the
HTML file itself small while still avoiding inline megabyte-scale payloads.
See `scripts/offline_toolkit/companion_data_writer.py`.

### 2. Split huge payloads into a "core" batch plus viewport-loaded chunks
A report with on the order of 100,000+ combined features has a companion
data file that's too large to parse comfortably before anything renders.
Splitting it into: (a) a small "core" batch of the largest/most significant
records (by whatever `size` proxy makes sense — length, area, priority
score) that loads immediately, and (b) the remainder split into numbered
chunk files, each tagged with a bounding box, that load lazily via
`<script>` tags as the reader pans/zooms into that area — keeps the initial
page load fast without discarding any data (a "load all now" control is
still offered for readers who want everything up front).

For chunk grouping, sort remaining records by a **Morton/Z-order key**
(interleaved quantised longitude/latitude bits) rather than by their
`size` proxy. Sorting by size alone gives every chunk a bounding box that
spans the whole dataset (because large/small features are scattered
everywhere), which defeats viewport-based loading; a spatial sort keeps
each chunk's bbox tight so panning/zooming only pulls in the chunks that
actually intersect the current view. See `scripts/offline_toolkit/companion_data_writer.py`.

### 3. Coalesce UI refreshes when chunks arrive in bursts
If viewport panning/zooming (or a "load all" action) triggers many chunk
loads in quick succession, and each chunk load naively re-renders the table/
map/legend, the tab can become unresponsive. Debounce the refresh (e.g. a
~300ms timer reset on each arrival) so a burst of chunks triggers one
refresh, not one per chunk.

### 4. Match the rendering strategy to the geometry type, not just feature count
A single "cap the total number of rendered features" rule works poorly
across geometry types. Point features cluster well (Leaflet's
`markercluster` plugin groups nearby points into a zoom-dependent cluster
marker, so all points can be "shown" even when there are hundreds of
thousands), but polylines/polygons don't cluster meaningfully — instead cap
*those* to the largest-N features currently in view (again ranked by a
`size` proxy) and communicate the cap in the UI ("N of M lines in view
shown, largest first"). Recompute the cap on every `moveend`, not just once
on load.

### 5. A small client-side "WHERE"-style query engine covers most ad hoc needs
Rather than standing up a database or query API, a single-file, dependency-
free expression matcher supporting `=`, `!=`, `>`, `>=`, `<`, `<=`, `LIKE`
(with `%wildcard%` translated to a regex) combined with `AND`/`OR`, matched
against each record's flattened properties plus a few well-known synonym
fields, covers the great majority of ad hoc filtering a reviewer will want
— without ever leaving the browser or exposing a real SQL surface. Document
clearly in the UI that this is a small expression matcher, not a real
database, so expectations are set correctly. See
`scripts/offline_toolkit/client_query_filter.js`.

### 6. Let readers save/share filter combinations without a backend
A "saved queries" feature backed by `localStorage` (scoped per report, so
different reports opened from different folders don't collide) lets a
reader capture a useful combination of dropdown filters + advanced query
text under a name, reload it later, and delete it — all without any server.
Adding JSON export/import on top lets saved queries be moved between
browsers/machines or backed up outside the browser, closing the main gap of
a purely local-storage approach. See `scripts/offline_toolkit/saved_queries.js`.

### 7. Use native `<details>/<summary>` for progressive disclosure
Marking supplementary sections (breakdown tables, provenance notes, "about
this report") as collapsible via `<details class="collapsible"><summary>...`
gives free, accessible, no-JavaScript-required expand/collapse behaviour
that still degrades gracefully if a browser blocks the report's scripts.
Keep the primary content (summary KPIs, map, results table) open by default
and collapse only the genuinely supplementary sections.

### 8. Decouple "what's exported" from "what's paginated"
Table pagination exists purely to keep the DOM light while browsing; it
should never limit what a "download matching records" action exports.
Export the *entire* currently filtered/queried set as CSV (flat attributes)
and/or GeoJSON (with geometry), independent of the page size currently
selected for on-screen browsing.

### 9. A synced hierarchical filter control suits nested categorical data
Where records naturally group hierarchically (for example a four- or
five-level classification), a collapsible tree-style map control — kept in
sync with cascading dropdown filters so selecting a parent narrows the
children shown in the next dropdown — reads far better than one flat
"pick a value" dropdown per level, especially once there are many distinct
leaf values.

### 10. Local GDAL via `ogr2ogr` needs no Python bindings and no pip installs
Shelling out to the `ogr2ogr` command-line tool from a local OSGeo4W (or
similar GDAL) installation — rather than a Python GDAL/Fiona binding — reads
a File Geodatabase (or any GDAL-supported source) with zero extra `pip
install`s. Reproject to WGS84 for display (`-t_srs EPSG:4326`), keep the
source projected CRS for any area/length calculations that need it, and
apply light geometry simplification (a couple of metres of tolerance) to
keep dense line/polygon layers responsive once loaded into a browser map.
See `scripts/offline_toolkit/ogr2ogr_gdb_extractor.py`.

### 11. Treat source data as strictly read-only, and say so in the report
Never modify the source workbook/geodatabase; only ever read from
it and write new, separate output files. Include an explicit "data
provenance and validation" section in the report itself, naming the exact
source file/worksheet/layer and generation timestamp, and stating how many
records were excluded and why (e.g. malformed coordinates) — this keeps the
report honest about its own limitations and traceable back to its source.

### 12. Compute normalised/derived fields once, at build time, not in the browser
Where a source field needs light normalisation for reporting (grouping
free-text categories, deriving a reporting period from a date, cleaning
numeric precision), do that once in the Python builder and carry the
derived field alongside the original in the record payload, rather than
re-deriving it repeatedly in client-side JavaScript. It's cheaper, easier
to test, and keeps the browser-side code simpler.

## Summary

None of the above requires a cloud spatial engine, a web server, or a paid
GIS licence — only a source dataset, Python, a local GDAL install for
geodatabase sources, and a modern browser. It complements, rather than
replaces, the cloud config-driven pipeline: pick whichever fits the
dataset size, refresh cadence, and infrastructure actually available.
