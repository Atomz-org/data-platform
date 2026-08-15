-- source extract for supplies (PII columns excluded by the MDL projection)
select supply_uuid, supply_id, product_id, supply_name, supply_cost, is_perishable_supply
from main_marts.supplies
