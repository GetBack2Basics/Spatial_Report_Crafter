#!/usr/bin/env python3
"""
CLI Script to compile standard Markdown proposals into standalone, client-editable HTML applications
with live dynamic cost worksheets.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from spatial_report_crafter import ProposalDocumentCrafter
except ImportError:
    from spatial_report_crafter.proposal_builder import ProposalDocumentCrafter


SAMPLE_MARKDOWN = """# Commercial Proposal & Spatial Engineering Scope

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
"""


def main():
    parser = argparse.ArgumentParser(description="Compile Markdown proposal into an interactive HTML application with live calculation worksheets.")
    parser.add_argument("--input", "-i", help="Path to input Markdown file. If omitted, generates a starter proposal.", default=None)
    parser.add_argument("--output", "-o", help="Path to output HTML file.", default="commercial_proposal_interactive.html")
    parser.add_argument("--title", "-t", help="Proposal Document Title", default="Commercial Proposal & Scope of Work")

    args = parser.parse_args()

    if args.input and Path(args.input).exists():
        with open(args.input, "r", encoding="utf-8") as f:
            md_content = f.read()
    else:
        print("[INFO] No input file specified or found. Using comprehensive default proposal template.")
        md_content = SAMPLE_MARKDOWN

    crafter = ProposalDocumentCrafter(title=args.title)
    out_path = crafter.compile_html(md_content, args.output)
    print(f"[SUCCESS] Compiled interactive proposal: {out_path}")


if __name__ == "__main__":
    main()
