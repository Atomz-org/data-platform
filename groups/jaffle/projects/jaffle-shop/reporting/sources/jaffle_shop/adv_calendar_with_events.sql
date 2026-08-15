-- source extract for adv_calendar_with_events (PII columns excluded by the MDL projection)
select date_day, day_name, is_weekend, week_start, month_start, event_count, category_count, event_types, event_categories, has_events
from main_marts.adv_calendar_with_events
