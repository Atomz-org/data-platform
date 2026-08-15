-- source extract for dim_suppliers (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, contact_name, contact_email, phone, address, city, state, country, is_active, created_at, total_contracts, active_contracts, min_contracted_lead_time_days, max_contracted_lead_time_days, earliest_contract_date, latest_contract_expiration
from main_marts.dim_suppliers
