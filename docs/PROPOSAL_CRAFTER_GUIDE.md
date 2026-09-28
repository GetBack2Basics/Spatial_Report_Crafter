# Guide: Building Interactive Proposals with Automated Calculation Worksheets 📝📊

This guide provides step-by-step instructions on how to use **Spatial Report Crafter** to compile client proposals into **standalone, interactive HTML applications** with live dynamic calculation worksheets.

---

## 🎯 What is the Proposal Crafter Engine?

Traditional proposals are delivered as static PDFs or Word documents. If a client or stakeholder wants to negotiate hours, test different billing rates, or add custom workstreams, it requires back-and-forth email exchanges and manual spreadsheet recalculation.

**Proposal Crafter solves this by embedding a live spreadsheet calculation engine into the proposal itself:**
1. **Real-Time Recalculation:** Changing any task's hours or rate immediately recalculates `hours × rate` for that row, updates the category subtotals, and updates the grand total and taxes in real-time.
2. **Interactive Row Actions:**
   - `▲` / `▼` : Reorder line items up or down.
   - `➕` : Add a new custom deliverable directly within any category group.
   - `✕` : Delete deliverable line items with instant total recalculation.
3. **Edit Mode vs. Locked View:** Toggle between `✏️ Edit Mode` (for drafting, reordering, and updating numbers) and `🔒 Locked View` (for clean, presentation-ready viewing where borders and action buttons disappear).
4. **Local Browser Auto-Save (`localStorage`):** Custom numbers and edits survive page refreshes and browser restarts.
5. **Clean 1-Click Clipboard Export:** The `📋 Copy for Google Docs` button strips out form inputs and generates clean, semantic HTML tables that paste perfectly into Google Docs or Microsoft Word.
6. **Print & PDF Optimized:** Includes `@media print` styles to output clean, professional PDFs with zero form input borders.

---

## 🛠️ Step-by-Step Compilation Workflow

### Method 1: Using the CLI Builder

```bash
# Compile any markdown proposal into an interactive HTML application
python scripts/build_proposal_document.py \
  --input my_proposal.md \
  --output client_proposal_v1.html \
  --title "Strategic Siting & Districting Proposal"
```

If you don't provide an input file, running `python scripts/build_proposal_document.py` will generate a sample proposal with all interactive features enabled.

---

### Method 2: Python SDK Integration

```python
from spatial_report_crafter import ProposalDocumentCrafter

# 1. Define custom categories and default deliverable line items
custom_categories = [
    {
        "id": "spatial_engineering",
        "title": "1. Spatial Data Engineering & Contiguity Modeling",
        "default_rate": 180,
        "items": [
            {"task": "GCS Lakehouse Ingestion & OSM Graph Prep", "desc": "Census ASGS ingestion & routing graph", "hours": 5.0, "rate": 180},
            {"task": "Adjacency Balancing & Contiguity Solver", "desc": "Graph-theoretic boundary expansion", "hours": 10.0, "rate": 180},
            {"task": "Triad QA Gate & Report Handover", "desc": "Zero-server HTML build & client walkthrough", "hours": 5.0, "rate": 180}
        ]
    },
    {
        "id": "platform_publishing",
        "title": "2. Enterprise Geospatial Platform Configuration",
        "default_rate": 150,
        "items": [
            {"task": "Enterprise Layer Schema Mapping", "desc": "Vector tiling & layer optimization", "hours": 8.0, "rate": 150},
            {"task": "Stakeholder Rollout & User Onboarding", "desc": "Role-based permissions & training", "hours": 6.0, "rate": 150}
        ]
    },
    {
        "id": "cloud_hosting",
        "title": "3. Platform Infrastructure & Hosting Subscriptions",
        "default_rate": "",
        "is_blank": True,
        "items": [
            {"task": "Annual Platform Hosting & Maintenance SLA", "desc": "Dedicated instance & database hosting", "hours": "", "rate": ""}
        ]
    }
]

# 2. Initialize the crafter
crafter = ProposalDocumentCrafter(
    title="National Siting & Districting Commercial Proposal",
    storage_key="client_proposal_v2_live",
    default_categories=custom_categories
)

# 3. Read your Markdown narrative
with open("docs/proposal_narrative.md", "r", encoding="utf-8") as f:
    markdown_content = f.read()

# 4. Compile to standalone interactive HTML
crafter.compile_html(
    markdown_text=markdown_content,
    output_path="docs/proposal_v2.html"
)
```

---

## 📋 Markdown Template Formatting

In your Markdown proposal, insert the placeholder `{{WORKSHEET}}` wherever you want the live calculation worksheet to appear:

```markdown
# Commercial Proposal & Spatial Engineering Scope

## 1. Executive Summary
This proposal outlines the technical scope, algorithmic districting architecture, and professional services required to deliver high-performance spatial intelligence models.

## 2. Technical Scope of Work
- **Authoritative Data Ingestion:** Census ASGS boundaries, road network routing graphs, and demographic deciles.
- **Topological Contiguity Solver:** Frontier expansion graph solver guaranteeing 100% contiguous territory boundaries.
- **Standalone WebGL Visualizer:** Hardware-accelerated client-side HTML suite delivered with $0.00 ongoing cloud compute fees.

## 3. Professional Services & Budget Allocation
Below is the interactive budget and deliverables worksheet. Adjust hours, rates, or add custom line items as required:

{{WORKSHEET}}

## 4. Quality Assurance & Sign-off
Deliverables are subjected to the strict Anti-Mock Triad QA gate:
1. Viewport feature count matches cloud storage records.
2. 100% topological contiguity certified across all zones.
3. Final standalone package verified for zero external server dependencies.
```

---

## ⚡ Client Interaction & Google Docs Export

When your client opens the generated `.html` file in Chrome, Edge, Safari, or Firefox:
1. **Edit Hours / Rates:** Any changes to numeric input fields trigger instant recalculations.
2. **Reorder & Add Deliverables:** Use `▲` / `▼` to reorder tasks or `➕` to add extra tasks under any category.
3. **Lock Document:** Clicking `🔒 Locked View` disables input controls and hides action buttons for a polished presentation.
4. **Export for Google Docs:** Clicking `📋 Copy for Google Docs` copies clean, formatted table HTML directly to the system clipboard. The user can simply press `Ctrl+V` (or `Cmd+V`) inside Google Docs or Word to paste formatted text tables without any raw `<input>` tags.
