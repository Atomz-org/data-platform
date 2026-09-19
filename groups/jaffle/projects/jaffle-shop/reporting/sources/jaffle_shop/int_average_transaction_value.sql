-- source extract for int_average_transaction_value (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    transaction_date,
    avg_transaction_value,
    rolling_7d_avg_atv,
    rolling_30d_avg_atv
from main_marts.int_average_transaction_value
