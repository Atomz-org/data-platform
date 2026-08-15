with

stores as (

    select
        location_id,
        location_name,
        opened_date,
        extract(year from opened_date) as opening_year
    from {{ ref('stg_locations') }}

),

monthly_orders as (

    select * from {{ ref('int_monthly_orders_by_store') }}

),

store_monthly as (

    select
        s.location_id,
        s.location_name,
        s.opening_year,
        mo.month_start,
        {{ dbt.datediff('s.opened_date', 'mo.month_start', 'month') }} as months_since_opening,
        mo.order_count,
        mo.total_revenue,
        mo.unique_customer_visits
    from stores as s
    inner join monthly_orders as mo
        on s.location_id = mo.location_id
    where mo.month_start >= s.opened_date

),

vintage_summary as (

    select
        opening_year,
        months_since_opening,
        count(distinct location_id) as stores_in_vintage,
        sum(order_count) as total_orders,
        sum(total_revenue) as total_revenue,
        avg(total_revenue) as avg_revenue_per_store,
        avg(order_count) as avg_orders_per_store,
        avg(unique_customer_visits) as avg_customers_per_store
    from store_monthly
    where months_since_opening between 0 and 24
    group by 1, 2

)

select * from vintage_summary
