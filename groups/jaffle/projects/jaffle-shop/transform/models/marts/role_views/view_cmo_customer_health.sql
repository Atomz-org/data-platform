with

customer_health as (
    select * from {{ ref('exec_customer_health_index') }}
)

select
    reporting_month,
    tracked_active_customers,
    churned_customers,
    customer_health_index,
    case
        when customer_health_index >= 80 then 'excellent'
        when customer_health_index >= 60 then 'good'
        when customer_health_index >= 40 then 'needs_attention'
        else 'critical'
    end as overall_customer_health
from customer_health
