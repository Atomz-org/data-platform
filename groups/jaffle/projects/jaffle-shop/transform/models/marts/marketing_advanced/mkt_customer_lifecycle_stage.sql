with

customers as (

    select
        customer_id,
        rfm_segment_code as rfm_segment,
        days_since_last_order,
        total_orders,
        first_order_at,
        last_order_at,
        lifetime_spend
    from {{ ref('dim_customer_360') }}

),

lapse_history as (

    select
        customer_id,
        count(case when days_between > 90 then 1 end) as lapse_count
    from (
        select
            customer_id,
            {{ dbt.datediff(
                'lag(ordered_at) over (partition by customer_id order by ordered_at)',
                'ordered_at',
                'day'
            ) }} as days_between
        from {{ ref('stg_orders') }}
    ) as gaps
    where days_between is not null
    group by 1

),

final as (

    select
        c.customer_id,
        c.total_orders,
        c.days_since_last_order,
        c.first_order_at,
        c.last_order_at,
        c.lifetime_spend,
        c.rfm_segment,
        coalesce(lh.lapse_count, 0) as historical_lapses,
        case
            when c.total_orders = 0 or c.total_orders is null then 'prospect'
            when c.total_orders = 1 and c.days_since_last_order <= 30 then 'new_customer'
            when c.days_since_last_order <= 60 and c.total_orders > 1 then 'active'
            when c.days_since_last_order between 61 and 120 then 'at_risk'
            when c.days_since_last_order > 120 and coalesce(lh.lapse_count, 0) > 0
                and c.days_since_last_order <= 180 then 'win_back'
            when c.days_since_last_order > 120 then 'churned'
            else 'unknown'
        end as lifecycle_stage
    from customers as c
    left join lapse_history as lh on c.customer_id = lh.customer_id

)

select * from final
