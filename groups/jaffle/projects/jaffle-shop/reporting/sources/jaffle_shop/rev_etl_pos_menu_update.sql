-- source extract for rev_etl_pos_menu_update (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, menu_category_id, price, is_active, description, synced_at, source_system
from main_marts.rev_etl_pos_menu_update
