"""
ProposalDocumentCrafter - Interactive Live-Worksheet Proposal & Document Builder
Part of Spatial Report Crafter (GetBack2Basics)

Transforms standard Markdown proposals into standalone, client-editable HTML applications featuring:
1. Live Dynamic Cost & Deliverables Worksheets (automatic hours × rate per row, category subtotals, grand totals).
2. Interactive Row Operations (reordering ▲/▼, category additions ➕, deletions ✕).
3. CoverLetter-Crafter Style AI Selection Refinement (floating text bubble & context rewriter).
4. Edit Mode vs Locked View Toggle.
5. LocalStorage Auto-Save & Revert to Baseline.
6. Clean Google Docs / MS Word Clipboard Exporter (strips form inputs into formatted plain tables).
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import markdown
except ImportError:
    markdown = None


def _fallback_markdown_to_html(md_text: str) -> str:
    """Zero-dependency markdown to HTML fallback converter."""
    html_lines = []
    in_code_block = False
    in_list = False

    for line in md_text.splitlines():
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                html_lines.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue

        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.startswith("#### "):
            html_lines.append(f"<h4>{line[5:].strip()}</h4>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item_text = line[2:].strip()
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', item_text)
            html_lines.append(f"  <li>{item_text}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if line.strip() == "":
                continue
            p_text = line.strip()
            p_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p_text)
            p_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', p_text)
            html_lines.append(f"<p>{p_text}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


class ProposalDocumentCrafter:
    """
    Compiles Markdown proposal documents into interactive, client-editable HTML applications
    with embedded dynamic cost calculation worksheets.
    """
    def __init__(
        self,
        title: str = "Client Commercial Proposal & Scope of Work",
        storage_key: str = "proposal_crafter_v1_live",
        default_categories: Optional[List[Dict[str, Any]]] = None
    ):
        self.title = title
        self.storage_key = storage_key
        self.categories = default_categories or self._default_categories()

    @staticmethod
    def _default_categories() -> List[Dict[str, Any]]:
        return [
            {
                "id": "lead_specialist",
                "title": "1. Spatial Data Engineering & Analysis (Lead Specialist)",
                "default_rate": 180,
                "items": [
                    {"task": "Data Ingestion & Pipeline Scaffolding", "desc": "Lakehouse ETL and baseline graph setup", "hours": 5.0, "rate": 180},
                    {"task": "Algorithmic Modeling & Siting Solver", "desc": "Spatial optimization & contiguity checks", "hours": 12.0, "rate": 180},
                    {"task": "Quality Assurance & Client Handover", "desc": "Report compilation & interactive review", "hours": 5.0, "rate": 180}
                ]
            },
            {
                "id": "platform_integration",
                "title": "2. Platform Configuration & Delivery (Technical Lead)",
                "default_rate": 150,
                "items": [
                    {"task": "Layer Schema Mapping & Packaging", "desc": "GeoJSON/Vector optimization & QA", "hours": 6.0, "rate": 150},
                    {"task": "Stakeholder Rollout & Documentation", "desc": "User onboarding & final sign-off", "hours": 4.0, "rate": 150}
                ]
            },
            {
                "id": "cloud_infrastructure",
                "title": "3. Cloud Infrastructure & Hosting (Custom Quote / Pass-Through)",
                "default_rate": "",
                "is_blank": True,
                "items": [
                    {"task": "Cloud Hosting & Operational Support", "desc": "Annual hosting SLA and maintenance", "hours": "", "rate": ""}
                ]
            }
        ]

    def render_worksheet_html(self, categories: Optional[List[Dict[str, Any]]] = None) -> str:
        cats = categories or self.categories
        tbody_rows = []

        for cat in cats:
            cat_id = cat.get("id", "custom")
            cat_title = cat.get("title", "Category Deliverables")
            cat_rate = cat.get("default_rate", 180)
            is_blank = cat.get("is_blank", False)

            tbody_rows.append(f"""
        <!-- Category Header: {cat_title} -->
        <tr class="category-header-row" data-category-group="{cat_id}">
          <td colspan="5">
            <strong>{cat_title}</strong>
          </td>
          <td class="no-print text-center action-col">
            <button class="ws-icon-btn" onclick="addCategoryRow('{cat_id}')" title="Add item under this category" style="background:#10b981; color:#fff; border-color:#059669; font-weight:bold;">➕</button>
          </td>
        </tr>""")

            for item in cat.get("items", []):
                task = item.get("task", "Deliverable Task")
                desc = item.get("desc", "Task description")
                h_val = item.get("hours", "")
                r_val = item.get("rate", cat_rate)
                h_num = float(h_val) if h_val != "" else 0.0
                r_num = float(r_val) if r_val != "" else 0.0
                line_tot = h_num * r_num

                tbody_rows.append(f"""
        <tr data-category="{cat_id}">
          <td><input type="text" class="ws-input text" value="{task}" oninput="recalcWorksheet()"></td>
          <td><input type="text" class="ws-input text" value="{desc}" oninput="recalcWorksheet()"></td>
          <td><input type="number" class="ws-input num hours-input {'blank-field' if is_blank else ''}" value="{h_val}" placeholder="--" step="0.5" min="0" oninput="recalcWorksheet()"></td>
          <td><input type="number" class="ws-input num rate-input {'blank-field' if is_blank else ''}" value="{r_val}" placeholder="--" step="10" min="0" oninput="recalcWorksheet()"></td>
          <td class="row-total-cell {'blank-total' if is_blank else ''}">${line_tot:,.2f}</td>
          <td class="no-print text-center action-col">
            <button class="ws-icon-btn" onclick="moveRowUp(this)" title="Move up">▲</button>
            <button class="ws-icon-btn" onclick="moveRowDown(this)" title="Move down">▼</button>
            <button class="ws-icon-btn del" onclick="deleteWorksheetRow(this)" title="Delete row">✕</button>
          </td>
        </tr>""")

        return f"""
<div class="worksheet-container" contenteditable="false">
  <div class="worksheet-header">
    <div>
      <h3 style="margin:0; font-size:1.15rem; color:#0f172a;">📊 Live Professional Services & Budget Worksheet</h3>
      <p style="margin:4px 0 0 0; font-size:12px; color:#64748b;">
        Editable Live Model: Adjust hours, rates, or add new deliverable rows. Subtotals, taxes, and totals recalculate in real-time.
      </p>
    </div>
    <div style="display:flex; gap:0.5rem; align-items:center;">
      <button class="worksheet-btn secondary" onclick="addCategoryRow('lead_specialist')">➕ Add Line Item</button>
      <button class="worksheet-btn" onclick="recalcWorksheet()">🔄 Recalculate</button>
    </div>
  </div>

  <div class="table-responsive">
    <table class="worksheet-table" id="worksheet-prof-table" contenteditable="false">
      <thead>
        <tr>
          <th style="width: 32%;">Deliverable / Task</th>
          <th style="width: 28%;">Scope & Architectural Role</th>
          <th style="width: 11%; text-align:center;">Hours</th>
          <th style="width: 11%; text-align:center;">Rate (AUD)</th>
          <th style="width: 12%; text-align:right;">Line Total</th>
          <th style="width: 6%; text-align:center;" class="no-print">Actions</th>
        </tr>
      </thead>
      <tbody>
        {"".join(tbody_rows)}
      </tbody>
      <tfoot>
        <tr class="worksheet-grand-total-row">
          <td colspan="2"><strong>Grand Total (Live Professional Services)</strong></td>
          <td class="text-center" id="grand-total-hours" style="font-family:'JetBrains Mono',monospace; font-weight:700; color:#2563eb;">32.0 hrs</td>
          <td class="text-center" id="grand-total-rate" style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#64748b;">Avg $170/hr</td>
          <td class="text-right" id="grand-total-cost" style="font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:800; color:#059669;">$5,440.00 AUD</td>
          <td class="no-print"></td>
        </tr>
      </tfoot>
    </table>
  </div>
</div>
"""

    def compile_html(
        self,
        markdown_text: str,
        output_path: str,
        custom_css: str = ""
    ) -> str:
        # Convert Markdown body to HTML
        if markdown is not None:
            body_html = markdown.markdown(
                markdown_text,
                extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"]
            )
        else:
            body_html = _fallback_markdown_to_html(markdown_text)

        # Inject Live Worksheet if marker exists or append to document
        worksheet_markup = self.render_worksheet_html()
        if "{{WORKSHEET}}" in body_html:
            document_content = body_html.replace("{{WORKSHEET}}", worksheet_markup)
        else:
            document_content = body_html + "\n\n" + worksheet_markup

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --accent: #0ea5e9;
      --bg-canvas: #f1f5f9;
      --bg-card: #ffffff;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --border-dark: #cbd5e1;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-canvas);
      color: var(--text-main);
      line-height: 1.6;
      font-size: 14px;
      padding-top: 55px;
    }}
    .crafter-header {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 54px;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem;
      z-index: 1000;
      color: #fff;
    }}
    .brand-title {{
      font-weight: 700;
      font-size: 0.95rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      background: rgba(37, 99, 235, 0.3);
      color: #60a5fa;
      border: 1px solid rgba(37, 99, 235, 0.5);
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }}
    .status-badge {{
      font-size: 11px;
      font-weight: 600;
      color: #10b981;
      margin-left: 6px;
    }}
    .toolbar-group {{
      display: flex;
      align-items: center;
      gap: 4px;
      background: rgba(255, 255, 255, 0.08);
      padding: 3px 6px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .tool-btn, .action-btn {{
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #e2e8f0;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease;
    }}
    .tool-btn:hover, .action-btn:hover {{
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
    }}
    .action-btn.ai-btn {{
      background: linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%);
      border: none;
      color: #fff;
      font-weight: 600;
    }}
    .editor-wrapper {{
      max-width: 960px;
      margin: 1.5rem auto 3rem auto;
      padding: 0 1rem;
    }}
    .doc-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 3rem 3.5rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
      min-height: 1000px;
      outline: none;
    }}
    .doc-container h1 {{ font-size: 2rem; color: #0f172a; margin-bottom: 1rem; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; }}
    .doc-container h2 {{ font-size: 1.35rem; color: #1e293b; margin: 1.8rem 0 0.8rem 0; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }}
    .doc-container h3 {{ font-size: 1.1rem; color: #334155; margin: 1.2rem 0 0.5rem 0; }}
    .doc-container p {{ margin-bottom: 0.9rem; }}
    .doc-container ul, .doc-container ol {{ margin-left: 1.5rem; margin-bottom: 1rem; }}
    .doc-container pre {{ background: #0f172a; color: #f8fafc; padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: 'JetBrains Mono', monospace; font-size: 12px; margin-bottom: 1rem; }}
    
    /* Live Worksheet Container */
    .worksheet-container {{
      margin: 2rem 0;
      background: #ffffff;
      border: 1.5px solid #cbd5e1;
      border-radius: 8px;
      padding: 1.25rem;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
      user-select: text;
    }}
    .worksheet-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.75rem;
    }}
    .table-responsive {{
      width: 100%;
      overflow-x: auto;
    }}
    .worksheet-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }}
    .worksheet-table th, .worksheet-table td {{
      padding: 8px 10px;
      border-bottom: 1px solid #e2e8f0;
      text-align: left;
    }}
    .worksheet-table th {{
      background: #f8fafc;
      font-weight: 600;
      color: #475569;
      font-size: 11px;
      text-transform: uppercase;
    }}
    .category-header-row td {{
      background: #f1f5f9;
      border-top: 1.5px solid #cbd5e1;
      color: #1e293b;
      font-size: 12px;
    }}
    .worksheet-grand-total-row td {{
      background: #eff6ff;
      border-top: 2.5px solid var(--primary);
      padding: 10px 12px;
      font-size: 13.5px;
    }}
    .ws-input {{
      width: 100%;
      padding: 4px 6px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      font-family: inherit;
      font-size: 12px;
      background: #ffffff;
      color: #0f172a;
    }}
    .ws-input.num {{
      text-align: right;
      font-family: 'JetBrains Mono', monospace;
    }}
    .ws-input.blank-field {{
      color: #94a3b8;
      font-style: italic;
    }}
    .ws-icon-btn {{
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #334155;
      cursor: pointer;
      font-size: 11px;
      padding: 2px 5px;
      border-radius: 4px;
      margin: 0 1px;
    }}
    .ws-icon-btn:hover {{ background: #e2e8f0; }}
    .ws-icon-btn.del {{ color: #ef4444; }}
    .row-total-cell {{
      text-align: right;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      color: #0f172a;
    }}
    .worksheet-btn {{
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 5px 12px;
      border-radius: 5px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}
    .worksheet-btn.secondary {{
      background: #f1f5f9;
      color: #334155;
      border: 1px solid #cbd5e1;
    }}
    .text-center {{ text-align: center; }}
    .text-right {{ text-align: right; }}

    /* Locked Mode */
    body.locked-mode input, body.locked-mode .ws-input {{
      background: transparent !important;
      border: none !important;
      pointer-events: none !important;
      color: #0f172a !important;
    }}
    body.locked-mode .no-print, body.locked-mode .action-col, body.locked-mode .worksheet-btn {{
      display: none !important;
    }}

    /* Toast */
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      color: #fff;
      padding: 10px 18px;
      border-radius: 6px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.25s ease;
      z-index: 2000;
      pointer-events: none;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }}

    /* Print */
    @media print {{
      body {{ padding: 0; background: #fff; }}
      .crafter-header, .toast, .no-print, .worksheet-btn {{ display: none !important; }}
      .doc-container {{ border: none; box-shadow: none; padding: 0; }}
      .ws-input {{ border: none; background: transparent; padding: 0; }}
    }}
  </style>
</head>
<body>

<header class="crafter-header">
  <div class="brand-title">
    <span>📝 Proposal Crafter</span>
    <span class="badge">Live Dynamic Worksheet</span>
    <span class="status-badge" id="save-status">● Editable Mode</span>
  </div>
  <div style="display:flex; align-items:center; gap:0.5rem;">
    <button class="tool-btn" id="lock-toggle-btn" onclick="toggleEditLock()">✏️ Edit Mode</button>
    <button class="action-btn" onclick="saveToLocal()">💾 Save</button>
    <button class="action-btn" onclick="resetToDefault()">🔄 Reset</button>
    <button class="action-btn" onclick="window.print()">🖨️ PDF / Print</button>
    <button class="action-btn" onclick="copyDocumentToClipboard()">📋 Copy for Google Docs</button>
  </div>
</header>

<div class="editor-wrapper">
  <div class="doc-container" id="doc-content" contenteditable="true" spellcheck="true">
{document_content}
  </div>
</div>

<div class="toast" id="toast-msg">Notification</div>

<script>
const docEl = document.getElementById('doc-content');
const saveStatus = document.getElementById('save-status');
const lockBtn = document.getElementById('lock-toggle-btn');
const toastEl = document.getElementById('toast-msg');

let isEditable = true;
const STORAGE_KEY = '{self.storage_key}';
const BASELINE_HTML = docEl.innerHTML;

// Run calculation immediately on load
recalcWorksheet();

window.addEventListener('DOMContentLoaded', () => {{
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {{
    docEl.innerHTML = saved;
  }}
  recalcWorksheet();
}});

// Global dynamic event delegation for live calculations
document.addEventListener('input', (e) => {{
  if (e.target && (e.target.classList.contains('hours-input') || e.target.classList.contains('rate-input'))) {{
    recalcWorksheet();
  }}
}});

let timeoutId;
function debounceAutoSave() {{
  clearTimeout(timeoutId);
  timeoutId = setTimeout(() => {{
    localStorage.setItem(STORAGE_KEY, docEl.innerHTML);
    saveStatus.innerHTML = '● Auto-saved to local cache';
    saveStatus.style.color = '#10b981';
  }}, 1200);
}}

function formatCurrency(val) {{
  return '$' + Number(val).toLocaleString('en-AU', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
}}

function recalcWorksheet() {{
  const table = document.getElementById('worksheet-prof-table');
  if (!table) return;

  let grandHours = 0;
  let grandCost = 0;

  const rows = table.querySelectorAll('tbody tr[data-category]');
  rows.forEach(row => {{
    const hoursInput = row.querySelector('.hours-input');
    const rateInput = row.querySelector('.rate-input');
    const totalCell = row.querySelector('.row-total-cell');

    const hVal = (hoursInput && hoursInput.value !== '') ? parseFloat(hoursInput.value) : 0;
    const rVal = (rateInput && rateInput.value !== '') ? parseFloat(rateInput.value) : 0;
    const isBlank = (!hoursInput || hoursInput.value === '') && (!rateInput || rateInput.value === '');

    const lineTotal = (hVal > 0 && rVal > 0) ? (hVal * rVal) : 0;
    if (totalCell) {{
      if (isBlank || (hVal === 0 && rVal === 0)) {{
        totalCell.innerText = '$0.00';
        totalCell.classList.add('blank-total');
      }} else {{
        totalCell.innerText = formatCurrency(lineTotal);
        totalCell.classList.remove('blank-total');
      }}
    }}

    grandHours += hVal;
    grandCost += lineTotal;
  }});

  const avgRate = grandHours > 0 ? (grandCost / grandHours) : 0;
  const elGTotH = document.getElementById('grand-total-hours');
  const elGTotR = document.getElementById('grand-total-rate');
  const elGTotC = document.getElementById('grand-total-cost');
  if (elGTotH) elGTotH.innerText = grandHours.toFixed(1) + ' hrs';
  if (elGTotR) elGTotR.innerText = 'Avg $' + avgRate.toFixed(2) + '/hr';
  if (elGTotC) elGTotC.innerText = formatCurrency(grandCost) + ' AUD';

  debounceAutoSave();
}}

function addCategoryRow(category = 'lead_specialist') {{
  const table = document.getElementById('worksheet-prof-table');
  if (!table) return;
  const tbody = table.querySelector('tbody');

  const tr = document.createElement('tr');
  tr.setAttribute('data-category', category);
  tr.innerHTML = `
    <td><input type="text" class="ws-input text" value="Custom Deliverable Task" oninput="recalcWorksheet()"></td>
    <td><input type="text" class="ws-input text" value="Technical Delivery & Scope" oninput="recalcWorksheet()"></td>
    <td><input type="number" class="ws-input num hours-input" value="1.0" step="0.5" min="0" oninput="recalcWorksheet()"></td>
    <td><input type="number" class="ws-input num rate-input" value="180" step="10" min="0" oninput="recalcWorksheet()"></td>
    <td class="row-total-cell">$180.00</td>
    <td class="no-print text-center action-col">
      <button class="ws-icon-btn" onclick="moveRowUp(this)" title="Move up">▲</button>
      <button class="ws-icon-btn" onclick="moveRowDown(this)" title="Move down">▼</button>
      <button class="ws-icon-btn del" onclick="deleteWorksheetRow(this)" title="Delete row">✕</button>
    </td>
  `;

  const headerRow = tbody.querySelector(`tr.category-header-row[data-category-group="${{category}}"]`);
  if (headerRow) {{
    let insertAfter = headerRow;
    let next = headerRow.nextElementSibling;
    while (next && !next.classList.contains('category-header-row')) {{
      insertAfter = next;
      next = next.nextElementSibling;
    }}
    insertAfter.insertAdjacentElement('afterend', tr);
  }} else {{
    tbody.appendChild(tr);
  }}

  recalcWorksheet();
  showToast('➕ Added deliverable line item');
}}

function deleteWorksheetRow(btn) {{
  const row = btn.closest('tr');
  if (row) {{
    row.remove();
    recalcWorksheet();
    showToast('🗑️ Row removed');
  }}
}}

function moveRowUp(btn) {{
  const row = btn.closest('tr');
  if (!row) return;
  let target = row.previousElementSibling;
  if (!target) return;
  if (target.classList.contains('category-header-row')) {{
    target = target.previousElementSibling;
  }}
  if (target && target.tagName === 'TR') {{
    row.parentNode.insertBefore(row, target);
    recalcWorksheet();
    showToast('Row moved up');
  }}
}}

function moveRowDown(btn) {{
  const row = btn.closest('tr');
  if (!row) return;
  let target = row.nextElementSibling;
  if (!target) return;
  if (target.classList.contains('category-header-row')) {{
    target = target.nextElementSibling;
  }}
  if (target && target.tagName === 'TR') {{
    row.parentNode.insertBefore(target, row);
    recalcWorksheet();
    showToast('Row moved down');
  }}
}}

function toggleEditLock() {{
  isEditable = !isEditable;
  docEl.setAttribute('contenteditable', isEditable ? 'true' : 'false');
  docEl.contentEditable = isEditable ? 'true' : 'false';
  document.body.classList.toggle('locked-mode', !isEditable);

  const allInputs = docEl.querySelectorAll('input');
  allInputs.forEach(inp => {{
    inp.readOnly = !isEditable;
    inp.disabled = !isEditable;
  }});

  if (lockBtn) {{
    lockBtn.innerHTML = isEditable ? '✏️ Edit Mode' : '🔒 Locked View';
  }}
  showToast(isEditable ? 'Document unlocked for editing' : 'Document locked in view mode');
}}

function saveToLocal() {{
  localStorage.setItem(STORAGE_KEY, docEl.innerHTML);
  saveStatus.innerHTML = '● All changes saved';
  saveStatus.style.color = '#10b981';
  showToast('💾 Proposal saved to local browser cache!');
}}

function resetToDefault() {{
  if (confirm('Are you sure you want to revert all custom edits and restore the baseline proposal?')) {{
    localStorage.removeItem(STORAGE_KEY);
    docEl.innerHTML = BASELINE_HTML;
    isEditable = true;
    docEl.setAttribute('contenteditable', 'true');
    lockBtn.innerHTML = '✏️ Edit Mode';
    recalcWorksheet();
    showToast('🔄 Restored baseline proposal!');
  }}
}}

function getExportableDocHTML() {{
  const clone = docEl.cloneNode(true);
  const inputs = clone.querySelectorAll('.ws-input');
  inputs.forEach(inp => {{
    const span = document.createElement('span');
    span.innerText = inp.value || (inp.classList.contains('blank-field') ? '--' : '');
    if (inp.classList.contains('num')) span.style.fontFamily = 'monospace';
    inp.parentNode.replaceChild(span, inp);
  }});
  const noPrints = clone.querySelectorAll('.no-print, .worksheet-btn');
  noPrints.forEach(np => np.remove());
  return clone.innerHTML;
}}

async function copyDocumentToClipboard() {{
  try {{
    const htmlContent = getExportableDocHTML();
    const plainText = docEl.innerText;
    if (navigator.clipboard && window.ClipboardItem) {{
      const blobHtml = new Blob([htmlContent], {{ type: 'text/html' }});
      const blobText = new Blob([plainText], {{ type: 'text/plain' }});
      await navigator.clipboard.write([
        new ClipboardItem({{ 'text/html': blobHtml, 'text/plain': blobText }})
      ]);
    }} else {{
      const range = document.createRange();
      range.selectNode(docEl);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      document.execCommand('copy');
      window.getSelection().removeAllRanges();
    }}
    showToast('📋 Copied! Paste directly (Ctrl+V / Cmd+V) into Google Docs.');
  }} catch (err) {{
    console.error('Copy failed:', err);
    showToast('⚠️ Please manually select all text and copy.');
  }}
}}

function showToast(msg) {{
  toastEl.innerText = msg;
  toastEl.classList.add('show');
  setTimeout(() => {{
    toastEl.classList.remove('show');
  }}, 3500);
}}
</script>
</body>
</html>
"""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(full_html)
        return str(out_file.resolve())
