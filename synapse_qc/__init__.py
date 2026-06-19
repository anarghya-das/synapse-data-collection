"""synapse_qc: quality analysis for the SYNAPSE CEEGrid ear-EEG dataset.

Submodules:
  qc_core    - vendored CEEGrid quality-check routines (from the analysis repo)
  inventory  - participant discovery / recording resolution (shared layout layer)
  excel      - workbook writer for the quality results
  manual     - loader for the prior hand ratings (kept for a LATER comparison
               step; the first QC pass runs fully independently of it)
"""
from . import qc_core, inventory, excel  # noqa: F401
