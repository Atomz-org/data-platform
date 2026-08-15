-- source extract for trend_inventory_movement_daily (PII columns excluded by the MDL projection)
select moved_at, location_id, inbound_qty, outbound_qty, total_absolute_quantity, inbound_7d_ma, outbound_7d_ma, net_movement, net_movement_7d_ma
from main_marts.trend_inventory_movement_daily
