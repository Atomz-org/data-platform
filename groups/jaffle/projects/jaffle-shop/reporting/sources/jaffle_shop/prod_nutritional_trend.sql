-- source extract for prod_nutritional_trend (PII columns excluded by the MDL projection)
select order_month, avg_calories_per_item, avg_fat_per_item, avg_protein_per_item, avg_carbs_per_item, total_items_sold, prev_month_calories, calorie_trend
from main_marts.prod_nutritional_trend
