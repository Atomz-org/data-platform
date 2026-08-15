with

orders as (

    select
        order_id,
        location_id,
        ordered_at,
        order_total,
        {{ dbt.date_trunc('day', 'ordered_at') }} as order_date,
        extract(hour from ordered_at) as order_hour
    from {{ ref('stg_orders') }}

),

with_daypart as (

    select
        order_id,
        location_id,
        order_date,
        order_total,
        order_hour,
        case
            when order_hour between 6 and 10 then 'morning'
            when order_hour between 11 and 14 then 'lunch'
            when order_hour between 15 and 17 then 'afternoon'
            when order_hour between 18 and 21 then 'evening'
            else 'late_night'
        end as daypart
    from orders

),

store_names as (

    select
        location_id,
        location_name as store_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        d.location_id,
        s.store_name,
        d.daypart,
        {{ dbt.date_trunc('month', 'd.order_date') }} as revenue_month,
        count(d.order_id) as order_count,
        sum(d.order_total) as total_revenue,
        avg(d.order_total) as avg_order_value,
        cast(count(d.order_id) as {{ dbt.type_float() }})
            / nullif(count(distinct d.order_date), 0) as avg_daily_orders
    from with_daypart as d
    inner join store_names as s
        on d.location_id = s.location_id
    group by 1, 2, 3, 4

)

select * from final
