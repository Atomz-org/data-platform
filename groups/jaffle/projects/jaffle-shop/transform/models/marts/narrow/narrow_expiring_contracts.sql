select
    supplier_id,
    expiration_date as contract_end_date,
    {{ dbt.datediff(dbt.current_timestamp(), "expiration_date", "day") }} as days_until_expiry
from {{ ref('stg_supplier_contracts') }}
where expiration_date >= {{ dbt.current_timestamp() }}
order by expiration_date asc
