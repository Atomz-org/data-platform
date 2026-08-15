with

customer_revenue as (
    select
        customer_id,
        sum(total_amount) as total_revenue
    from {{ ref('fct_invoices') }}
    group by 1
),

customer_orders as (
    select
        customer_id,
        location_id,
        count(*) as customer_orders
    from {{ ref('stg_orders') }}
    group by 1, 2
),

final as (
    select
        cr.customer_id,
        cr.total_revenue,
        case
            when cr.total_revenue > 500 then 'high_value'
            when cr.total_revenue > 100 then 'medium_value'
            else 'low_value'
        end as profitability_tier
    from customer_revenue as cr
)

select * from final
