"""
Spatial Report Crafter (SpatialReportCrafter)
Enterprise toolkit and architectural method for building zero-server Map-in-a-Box interactive spatial HTML reports,
dynamic cost calculation worksheets, and architectural lessons learned suites.
"""

from .builder import SpatialReportCrafter
from .proposal_builder import ProposalDocumentCrafter

__all__ = ["SpatialReportCrafter", "ProposalDocumentCrafter"]
__version__ = "2.3.0"
