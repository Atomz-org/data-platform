-- source extract for narrow_expiring_contracts (PII columns excluded by the MDL projection)
select supplier_id, contract_end_date, days_until_expiry
from main_marts.narrow_expiring_contracts
