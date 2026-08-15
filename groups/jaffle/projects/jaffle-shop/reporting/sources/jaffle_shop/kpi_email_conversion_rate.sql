-- source extract for kpi_email_conversion_rate (PII columns excluded by the MDL projection)
select email_month, sent, opened, clicked, converted, open_rate, click_to_open_rate, conversion_rate
from main_marts.kpi_email_conversion_rate
