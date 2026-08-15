with

mr as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

store_tenure as (

    select
        location_id,
        opened_date,
        {{ dbt.datediff('opened_date', 'current_date', 'month') }} as months_open
    from {{ ref('stg_locations') }}

),

qualified_stores as (

    select location_id
    from store_tenure
    where months_open >= 12

),

monthly_rev as (

    select
        mr.location_id,
        mr.store_name,
        mr.month_start,
        mr.monthly_revenue,
        mr.monthly_orders
    from mr
    inner join qualified_stores as qs
        on mr.location_id = qs.location_id

),

with_growth as (

    select
        location_id,
        store_name,
        month_start,
        monthly_revenue,
        monthly_orders,
        lag(monthly_revenue, 12) over (
            partition by location_id order by month_start
        ) as revenue_same_month_last_year,
        lag(monthly_orders, 12) over (
            partition by location_id order by month_start
        ) as orders_same_month_last_year
    from monthly_rev

),

final as (

    select
        location_id,
        store_name,
        month_start,
        monthly_revenue,
        monthly_orders,
        revenue_same_month_last_year,
        orders_same_month_last_year,
        case
            when revenue_same_month_last_year > 0
            then (monthly_revenue - revenue_same_month_last_year)
                / revenue_same_month_last_year * 100
            else null
        end as same_store_revenue_growth_pct,
        case
            when orders_same_month_last_year > 0
            then (monthly_orders - orders_same_month_last_year)
                / cast(orders_same_month_last_year as {{ dbt.type_float() }}) * 100
            else null
        end as same_store_order_growth_pct
    from with_growth
    where revenue_same_month_last_year is not null

)

select * from final
