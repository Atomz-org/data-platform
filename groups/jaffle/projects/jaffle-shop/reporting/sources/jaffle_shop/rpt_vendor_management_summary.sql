-- source extract for rpt_vendor_management_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    vendor_classification
from main_marts.rpt_vendor_management_summary
