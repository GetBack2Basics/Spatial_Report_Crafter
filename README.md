# Spatial Report Crafter 🗺️📦

**Spatial Report Crafter** is an enterprise-grade toolkit and architectural method for building **'Map-in-a-Box'** interactive spatial HTML reports, multi-criteria decision analysis (MCDA) engines, and geospatial audit dashboards.

It compiles massive spatial datasets (queried across millions of geometries via **Wherobots Cloud / Apache Sedona** or local **GeoPackages**), live government WMS/REST feeds, and multi-criteria constraint models into a **single, zero-dependency, standalone HTML document** that runs entirely in any modern web browser with **$0.00 ongoing cloud compute cost**.

---

## 🚀 The 'Map-in-a-Box' Philosophy

Traditional geospatial reporting suffers from a fundamental tradeoff: either deliver static PDF/Word maps that cannot be interrogated, or host heavy web GIS servers (GeoServer, ArcGIS Enterprise, Mapbox GL) that require costly running infrastructure, cloud licenses, and backend database connections.

**Spatial Report Crafter solves this via client-side compilation:**
- **Zero Cloud Compute Latency**: The heavy spatial work (topological buffers, `ST_Difference` masks, contour winding distances) is computed once on cloud spatial engines (Wherobots/Sedona) and embedded as structured GeoJSON/JSON payloads.
- **Sub-Millisecond Slider Interactivity**: Multi-criteria weight sliders and scenario toggles run 100% in-browser via JavaScript, re-scoring candidates and updating leaderboards in **< 1 millisecond** without server round-trips.
- **Complete Open Evidence Trail**: Integrates interactive maps, live transmission feeds, side-by-side ground-truth audit panels, data provenance tables, and reproducible SQL trails into a single shareable document.

```mermaid
flowchart TD
    subgraph DataSources["1. Authoritative Data & Cloud Spatial SQL"]
        WB["Wherobots Cloud (Apache Sedona) / GeoPackage"]
        SRC["National / State Portals (Cadastre, Grid, DEM, POIs)"]
        SRC --> WB
    end

    subgraph Compiler["2. Spatial Report Crafter Compiler"]
        PY["build_config_report.py / Python Builder"]
        CFG["configs/national_suitability.json"]
        TPL["templates/national_suitability_report_template.html"]
        DOCS["Recent Changes & Next Steps Markdown"]
        
        WB -->|GeoJSON & Candidate Data| PY
        CFG --> PY
        TPL --> PY
        DOCS --> PY
    end

    subgraph Output["3. Standalone 'Map-in-a-Box' Report (.html)"]
        HTML["Self-Contained Interactive Document
(Zero Server Dependencies)"]
        PY --> HTML
    end

    subgraph Client["4. In-Browser Client Execution ($0.00 Cost)"]
        HTML --> M["Leaflet / MapLibre Interactive Map & WMS"]
        HTML --> S["What-If Multi-Criteria Sandbox (<1ms Recalculation)"]
        HTML --> L["Ranked Leaderboard & Lot/Plan Search"]
        HTML --> A["Proponent Claim vs. Ground-Truth Audit Panel"]
        HTML --> E["10-Tab Evidence, Provenance & Speed Trail"]
    end
```

---

## 🛠️ The 4-Stage Method for Creating Spatial HTML Reports

### Stage 1: Spatial Data Extraction & Database Ingestion
1. **Coordinate Reference System (CRS) Normalization**: Standardize all layers into an official metric projected CRS (e.g. `EPSG:7856` GDA2020 / MGA Zone 56 or `EPSG:3112` Geoscience Australia Lambert) for accurate distance buffers and area calculations. Keep output display geometries in `EPSG:4326` (WGS84).
2. **Topology Verification & Repair**: Always sanitize geometries with `ST_MakeValid` and filter out degenerate geometries prior to aggregation.
3. **Data Fingerprinting & Memoization**: Use cryptographic hashing (ETags, GeoParquet file hashes, Iceberg snapshot IDs) to skip re-ingesting untouched spatial layers.

### Stage 2: Decoupled Incremental Spatial Processing
To optimize compute costs and allow rapid parameter iteration:
- **Decouple Heavy Geometry from Lightweight Scoring**: Execute topological buffering (30m riparian, 20m pipelines), polygon difference overlays (`ST_Difference`), and network winding distance matrices once.
- **Downstream Scoring**: Evaluate mathematical decay curves ($S_{\text{power}}$, $S_{\text{sensitive}}$, $S_{\text{water}}$) and continuous sigmoidal functions independently without re-triggering heavy spatial joins:
  $$S_{\text{sensitive}}(d) = \frac{1}{1 + e^{-k(d - d_0)}}$$

### Stage 3: Template-Driven Report Assembly
The Python report builder (`scripts/build_config_report.py`) dynamically compiles the final HTML document:
1. **Config-Driven Query Execution**: Maps SQL queries in `configs/*.json` to specific GeoJSON layer placeholders.
2. **Dynamic Metadata & Volume Ingestion**: Queries database row counts dynamically to build the provenance evidence table.
3. **Markdown Documentation Folding**: Automatically converts `walkthrough.md`, `next_steps.md`, or `recent_changes.md` into integrated tabs within the report.
4. **Escaped Template Safety**: Strictly handles multiline string escapes (e.g. `\\n`) to prevent JavaScript template syntax errors.

### Stage 4: Zero-Cost Client-Side Simulation & Analytics
1. **Interactive What-If Sandbox**: In-browser JavaScript sliders dynamically re-normalize weights to 1.0 and re-evaluate composite candidate scores in `< 1ms`.
2. **Scenario Toggles**: Instant hazard / easement switches (e.g., TSF Dam Safety) swap polygon layers and update net developable pad statistics instantly.
3. **GeoLibre & DuckDB-WASM Ready**: Output GeoParquet layers can be queried serverless via [opengeos/GeoLibre](https://github.com/opengeos/GeoLibre) using DuckDB-WASM over HTTP byte-range requests.

---

## 📋 Core Dashboard Component Architecture

A complete **Spatial Report Crafter** document incorporates the following standard modules:

| Component | Purpose & Features |
| :--- | :--- |
| **1. Header & KPI Metric Strip** | Displays high-level KPIs with CSS hover tooltips and accessible `ℹ` footnote links (e.g. Candidates, Geometries, Join Speed, Batch Compute Cost). |
| **2. Multi-Factor What-If Sandbox** | Real-time sliders for Power, Recycled Water, Sensitive Setbacks, and Parcel Size, with interactive scenario toggle switches. |
| **3. Interactive Continental Map** | Leaflet/MapLibre map with shaded relief basemaps, custom collapsible layer controls, clustered substations, and live WMS/ArcGIS Dynamic feeds (e.g. Geoscience Australia electricity grid). |
| **4. Ranked Leaderboard & Search** | Sortable table with dynamic score bars, locality filters, and live Lot/Plan cadastre search (e.g. `101//DP755262`). Clicking rows smoothly pans the map. |
| **5. Proponent Audit Panel** | Side-by-side ground-truth audit verifying net developable pad space (deducting riparian, pipeline, slope >5%), topological network routing (1.32x winding factor), and thermodynamic heat drop. |
| **6. Multi-Tab Evidence Trail** | 10 integrated tabs: State Benchmarking, Regional Aggregates, Data Sources & Volumes, Lakehouse Storage Directory Tree, Table Footprints, Whitepapers, Speed Mechanics, Calculations & SQL Trail, Recent Changes, and Next Steps. |

---

## 💻 Quickstart & Usage

### 1. Cloud-Based Spatial Reporting (Wherobots / Apache Sedona)

Generate interactive, config-driven reports directly from cloud database clusters:

```bash
# Ensure WHEROBOTS_API_KEY is configured in your environment or .env
python scripts/build_config_report.py \
  --config configs/national_suitability.json \
  --template templates/national_suitability_report_template.html \
  --output Siting_Suitability_Report.html
```

### 2. Offline GIS Desktop Reporting (GeoPackage)

Build interactive reconciliation reviews and displacement maps from local GeoPackage layers:

```bash
python scripts/build_html_report.py \
  --gpkg "Pending Data/Critical_Review_Assets.gpkg" \
  --output Reconciliation_Report.html
```

---

## ⚙️ Configuration Schema (`configs/national_suitability.json`)

```json
{
  "report_title": "National Siting Suitability Report",
  "project_crs": "EPSG:7856",
  "wherobots_queries": {
    "main_suitability": "SELECT * FROM org_catalog.fgsdb.candidate_suitability"
  },
  "local_vector_layers": [
    {
      "name": "Net Developable Pad Space",
      "placeholder": "__NET_DEVELOPABLE_GEOJSON__",
      "query": "SELECT precinct_key, net_developable_geom FROM org_catalog.fgsdb.net_developable_zones",
      "properties_map": { "precinct_key": 0 },
      "geometry_index": 1
    }
  ],
  "wms_services": [
    {
      "name": "GA National Transmission Grid",
      "url": "https://services.ga.gov.au/gis/rest/services/Electricity_Infrastructure/MapServer",
      "type": "esri-dynamic"
    }
  ]
}
```

---

## 🏆 Production References & Examples

- **Showcase Implementation**: [hunter_spatial_crafter](https://github.com/GetBack2Basics/hunter_spatial_crafter) — National AI Data Center Siting Engine querying 15.91M geometries.
- **Live Interactive Demo**: [national-suitability-report.vercel.app](https://national-suitability-report.vercel.app)
- **Engineering Playbook**: [wherobots_antigravity_playbook.md](https://github.com/GetBack2Basics/CheatSheets/blob/main/wherobots_antigravity_playbook.md)
- **Word/DOCX Generation**: [Spatial_Document_Crafter](https://github.com/GetBack2Basics/Spatial_Document_Crafter)
- **Open-Source Web Platform**: [opengeos/GeoLibre](https://github.com/opengeos/GeoLibre)

---

## 📴 Offline / No-Cloud Option

Not every deployment has a cloud spatial engine available. For teams
building standalone reports from local sources (Excel workbooks,
GeoPackages, File Geodatabases) with no server and $0 cloud compute:

- **Lessons learned**: [`docs/lessons_learned_offline_case_study.md`](docs/lessons_learned_offline_case_study.md) — a schema-free write-up of patterns discovered running this method fully offline (companion data files instead of `fetch()`, viewport-triggered spatial chunk loading, geometry-appropriate rendering, a client-side query engine, `localStorage` saved queries, and more).
- **Reusable code**: [`scripts/offline_toolkit/`](scripts/offline_toolkit/) — the schema-free, standalone implementations of those patterns.

---

## 📜 License
MIT License — Copyright (c) 2026 George Chandeep Corea (GetBack2Basics).
