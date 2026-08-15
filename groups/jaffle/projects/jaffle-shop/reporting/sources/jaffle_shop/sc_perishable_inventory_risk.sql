-- source extract for sc_perishable_inventory_risk (PII columns excluded by the MDL projection)
select product_id, location_id, ingredient_name, ingredient_category, current_quantity, daily_depletion_rate, estimated_days_supply, spoilage_risk
from main_marts.sc_perishable_inventory_risk
