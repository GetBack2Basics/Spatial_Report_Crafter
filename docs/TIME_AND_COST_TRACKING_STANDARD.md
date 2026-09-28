# Spatial Engineering Project Standard: Time & Cost Tracking Protocol (TCTP)

> **Mandatory Standard:** Every spatial data engineering, districting, and geospatial visualization project must maintain a live, auditable `TIME_AND_COST_LOG.md` and embed interactive live calculation worksheets into client proposals.

---

## 1. Objectives & Principles

1. **Radical Transparency:** Clear attribution of human effort (PM, client review, QA sign-off), machine AI orchestration time, cloud compute runtimes (GCE, Valhalla, Sedona), and platform hosting.
2. **Dynamic Worksheets vs. Static PDF Tables:** Proposals must provide live interactive worksheets where hours and rates can be adjusted with instant subtotal and grand total recalculation, dynamic custom line-item additions (`+ Add Item`), and customizable blank points for partner platform subscriptions (e.g. enterprise software licenses or custom hosting).
3. **Capacity & Margin Reconciliation:** Continuous tracking of spent actuals against budget baselines prevents scope creep and protects project profitability.
4. **Zero-Hallucination Triad QA:** Reconciling Viewport Feature Count == Cloud Storage Records == Authoritative Source Records.

---

## 2. Standard Time & Cost Log Structure (`TIME_AND_COST_LOG.md`)

Every repository must include a root `TIME_AND_COST_LOG.md` structured with the following sections:

### Section 1: Budget Summary Dashboard
A high-level reconciliation table outlining:
- Workstream / Lead Actor
- Scope & Detailed Activities
- Budget Baseline (Hours)
- Logged Effort (Actuals)
- Hard Cost Forecast (AUD)
- Status (`COMPLETED`, `IN PROGRESS`, `SCHEDULED`, `ON TRACK`)

### Section 2: Granular Time & Compute Log
A row-by-row event log tracking every milestone and iterative change:
| Column | Format / Description | Example |
| :--- | :--- | :--- |
| **Entry ID** | `LOG-001`, `LOG-002`, ... | `LOG-028` |
| **Date / Time** | ISO / Local AEDT Timestamp | `2026-09-28 12:08` |
| **Phase** | `Setup`, `Phase 1`, `Phase 2`, `Districting`, `UI/UX`, `Governance` | `UI / Map UX` |
| **Actor / Resource** | Human Engineer, AI Machine, Cloud VM, Spatial Cluster | `Antigravity AI (Machine)` |
| **Activity / Task** | Detailed description of technical actions and design decisions | `Upgraded popup dragging engine into floating HUD...` |
| **Duration (Mins/Hrs)** | Minutes and Decimal Hours | `15 mins` / `0.25 hrs` |
| **Unit Cost / Rate** | Hourly rate, Token cost, or Cloud compute rate | `Token / Orchestration` |
| **Est. Cost (AUD)** | Calculated cost in AUD | `~$0.10` |
| **Artifacts** | Clickable links to code, configs, or deployed reports | `scripts/run_seq_partition_23.py` |

### Section 3: Actor Classifications & Cloud Resources
Standard taxonomy for logged actors:
1. **Human (Client / Lead Spatial Engineer / PM):** Review meetings, architecture alignment, parameter sign-off.
2. **Machine (AI Orchestrator / Antigravity):** Pipeline scaffolding, code generation, schema validation, test runs.
3. **Machine (Cloud - Valhalla GCE):** Dedicated VM runtime for routing graph compilation and isochrone computation.
4. **Machine (Cloud - Wherobots / Apache Sedona):** Spatial Unit (SU) execution for distributed polygon joins (`ST_Intersects`).
5. **Machine (Cloud - GCS / CDN):** Static hosting, tile serving, data ingress/egress.

---

## 3. SpatialReportCrafter Live Worksheet & Lessons Learned Integration

When delivering spatial QA suites or commercial proposals via `SpatialReportCrafter`:
1. **Turnkey Configuration Flags**:
   - `include_cost_worksheet=True`: Embeds an interactive, reactive cost and deliverables worksheet directly into the zero-server WebGL application.
   - `include_lessons_learned=True`: Embeds structured architectural lessons learned cards documenting graph adjacency solvers, zero-server compute, and time & cost protocols.
2. **Live Number Inputs**: Hourly allocations and unit rates are editable `<input type="number">` fields.
3. **Real-Time Recalculation**: Changing any value instantly updates row totals (`hours × rate`), subtotal summaries, and grand totals across the document.
4. **Partner Platform Blank Point**: Partner subscriptions (e.g., enterprise GIS platform licenses, user seats, and hosting SLAs) are provided as customizable line items with initial blank values (`--` / `$0.00`) ready for partner pricing.
5. **Google Docs & Print Serialization**: Export mechanisms cleanly serialize active input values into standard table text so the document pastes seamlessly into Google Docs or exports to PDF without raw form inputs.

### Python API Example:
```python
from spatial_report_crafter import SpatialReportCrafter

crafter = SpatialReportCrafter(
    title="National Territory Mapping Suite",
    mask_opacity=0.75,
    include_cost_worksheet=True,      # Enables live dynamic calculation worksheet
    include_lessons_learned=True       # Enables architectural lessons learned tab
)

crafter.generate_html_report(
    territories_gdf=territories,
    postcodes_gdf=postcodes,
    seeds_gdf=seeds,
    catchments_gdf=catchments,
    output_html_path="docs/districting_suite.html",
    summary_stats=stats
)
```

---

## 4. Template Starter for New Projects

```markdown
# [Project Name] — Time & Cost Tracking Log

> **Tracking Policy:** All human review/QA time and machine/cloud compute time must be logged against budget estimates.

## 1. Budget Summary Dashboard
| Workstream / Actor | Scope | Budget Hours | Actual Hours | Hard Cost (AUD) | Status |
|---|---|---|---|---|---|
| **Lead Spatial Engineer** | Ingestion, Analysis & Districting | 35.0 hrs | 0.0 hrs | ~$25.00 | READY |
| **Platform Integration** | Platform Ingestion & User Setup | 15.0 hrs | 0.0 hrs | — | SCHEDULED |

## 2. Granular Time & Compute Log
| Entry ID | Date / Time | Phase | Actor / Resource | Activity / Task | Duration | Rate | Est. Cost (AUD) | Artifacts |
|---|---|---|---|---|---|---|---|---|
| `LOG-001` | YYYY-MM-DD | Setup | AI Machine | Repository Scaffolding | 10 mins | Token | ~$0.05 | `src/` |
```
