-- source extract for dist_basket_size (PII columns excluded by the MDL projection)
select basket_size, order_count, mean_basket, median_basket, p75_basket, p90_basket
from main_marts.dist_basket_size
