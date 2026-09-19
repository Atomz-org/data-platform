-- source extract for int_email_send_time_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    hour_of_day,
    day_of_week,
    open_rate,
    click_rate
from main_marts.int_email_send_time_analysis
