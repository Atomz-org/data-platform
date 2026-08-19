-- source extract for coh_product_adoption_curve (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    product_name,
    first_sale_date,
    units_first_30d,
    units_first_90d,
    revenue_first_180d
from main_marts.coh_product_adoption_curve
