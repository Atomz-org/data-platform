select
    case
        when opened_date <= current_date then true
        else false
    end as is_open,
    count(*) as store_count
from {{ ref('stg_locations') }}
group by 1
