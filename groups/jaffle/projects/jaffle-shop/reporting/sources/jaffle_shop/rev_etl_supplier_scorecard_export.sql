-- source extract for rev_etl_supplier_scorecard_export (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, fulfillment_rate, total_purchase_orders, supplier_status, exported_at
from main_marts.rev_etl_supplier_scorecard_export
