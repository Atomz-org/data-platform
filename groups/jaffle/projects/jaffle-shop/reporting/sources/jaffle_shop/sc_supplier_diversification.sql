-- source extract for sc_supplier_diversification (PII columns excluded by the MDL projection)
select product_id, total_suppliers, active_suppliers, total_line_items, diversification_status, supply_risk_level
from main_marts.sc_supplier_diversification
