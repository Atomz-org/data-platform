-- source extract for int_product_affinity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id_a,
    product_id_b,
    co_occurrence_count,
    support_a,
    support_b,
    affinity_rank
from main_marts.int_product_affinity
