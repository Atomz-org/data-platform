-- source extract for stg_derived_menu_item_with_nutrition (PII columns excluded by the MDL projection)
select menu_item_id, product_id, menu_item_name, menu_item_price, calories, protein_g, total_fat_g, total_carbs_g, dietary_fiber_g, sodium_mg
from main_marts.stg_derived_menu_item_with_nutrition
