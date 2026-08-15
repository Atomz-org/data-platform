-- source extract for rpt_nutrition_compliance (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, menu_item_size, category_name, product_type, is_available, calories, total_fat_g, sodium_mg, total_sugars_g, protein_g, caffeine_mg, exceeds_calorie_threshold, exceeds_high_calorie_threshold, exceeds_sodium_threshold, exceeds_sugar_threshold, exceeds_caffeine_threshold, compliance_status, flag_count
from main_marts.rpt_nutrition_compliance
