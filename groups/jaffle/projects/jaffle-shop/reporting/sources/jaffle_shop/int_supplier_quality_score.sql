-- source extract for int_supplier_quality_score (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    total_quantity_received,
    total_quantity_rejected,
    defect_rate,
    quality_score,
    total_waste_quantity,
    total_waste_cost
from main_marts.int_supplier_quality_score
