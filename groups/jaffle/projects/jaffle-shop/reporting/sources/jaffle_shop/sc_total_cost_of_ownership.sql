-- source extract for sc_total_cost_of_ownership (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, total_material_cost, total_delivery_cost, quality_loss_cost, admin_cost, total_cost_of_ownership, tco_multiplier
from main_marts.sc_total_cost_of_ownership
