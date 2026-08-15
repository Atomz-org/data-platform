with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

monthly_customers as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(distinct customer_id) as unique_customers

    from orders
    where customer_id is not null
    group by location_id, {{ dbt.date_trunc('month', 'ordered_at') }}

),

with_trend as (

    select
        mc.location_id,
        l.location_name as store_name,
        mc.order_month,
        mc.unique_customers,
        lag(mc.unique_customers) over (
            partition by mc.location_id order by mc.order_month
        ) as prev_month_customers,
        round(
            (mc.unique_customers - lag(mc.unique_customers) over (
                partition by mc.location_id order by mc.order_month
            )) * 100.0
            / nullif(lag(mc.unique_customers) over (
                partition by mc.location_id order by mc.order_month
            ), 0), 2
        ) as mom_growth_pct

    from monthly_customers mc
    left join locations l on mc.location_id = l.location_id

)

select
    location_id,
    store_name,
    order_month,
    unique_customers,
    prev_month_customers,
    mom_growth_pct,
    case
        when mom_growth_pct > 5 then 'growing'
        when mom_growth_pct >= -5 then 'stable'
        else 'declining'
    end as customer_trend

from with_trend
