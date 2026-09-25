# Offline toolkit

Schema-free, reusable code extracted from an offline "Map-in-a-Box" case
study (see [`../../docs/lessons_learned_offline_case_study.md`](../../docs/lessons_learned_offline_case_study.md)
for the full write-up of *why* each pattern exists). None of these files
contain any project data, field names, or schema — every example uses
generic placeholders and is meant to be adapted to your own dataset shape.

This complements the cloud config-driven pipeline
(`build_config_report.py` / `configs/*.json` / `templates/*.html`) as an
"Option B" for teams building standalone reports from local sources
(Excel workbooks, GeoPackages, File Geodatabases) without a cloud spatial
engine.

| File | Purpose |
| --- | --- |
| `companion_data_writer.py` | Writes a report's JSON payload to a companion `<script src>` `_data.js` file instead of inlining it in the HTML (works from a bare `file://` URL); splits very large payloads into a largest-first "core" batch plus viewport-loadable spatial "chunk" files. |
| `client_query_filter.js` | A small, dependency-free "WHERE"-style expression matcher (`=`, `!=`, `>`, `>=`, `<`, `<=`, `LIKE`, `AND`/`OR`) for ad hoc client-side filtering of an in-memory record set. |
| `saved_queries.js` | A `localStorage`-backed "saved queries" module (save/load/delete/export/import) for letting report readers keep named filter combinations without a backend. |
| `ogr2ogr_gdb_extractor.py` | Shells out to a local GDAL (`ogr2ogr`, e.g. via an OSGeo4W install) to export a File Geodatabase layer to reprojected, optionally simplified GeoJSON — no Python GDAL bindings or `pip install` required. |
| `rendering_patterns.md` | Snippets for geometry-appropriate map rendering (point clustering vs. viewport largest-first caps for lines/polygons) and native `<details>/<summary>` collapsible sections. |

Each file is self-contained and can be copied into a project and adapted,
or used as a reference implementation.
