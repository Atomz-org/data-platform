with

orders as (

    select * from {{ ref('stg_orders') }}

),

monthly_primary_store as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        location_id,
        count(*) as orders_at_store,
        row_number() over (
            partition by customer_id, {{ dbt.date_trunc('month', 'ordered_at') }}
            order by count(*) desc
        ) as store_rank

    from orders
    where customer_id is not null
    group by customer_id, {{ dbt.date_trunc('month', 'ordered_at') }}, location_id

),

primary_stores as (

    select
        customer_id,
        order_month,
        location_id as primary_store_id,
        orders_at_store

    from monthly_primary_store
    where store_rank = 1

),

migrations as (

    select
        curr.customer_id,
        curr.order_month,
        prev.primary_store_id as previous_store_id,
        curr.primary_store_id as current_store_id,
        case
            when prev.primary_store_id is null then 'new_customer'
            when prev.primary_store_id = curr.primary_store_id then 'retained'
            else 'migrated'
        end as migration_status

    from primary_stores curr
    left join primary_stores prev
        on curr.customer_id = prev.customer_id
        and curr.order_month = prev.order_month + interval '1 month'

)

select
    order_month,
    migration_status,
    count(distinct customer_id) as customer_count,
    round(
        (count(distinct customer_id) * 100.0
        / nullif(sum(count(distinct customer_id)) over (partition by order_month), 0)), 2
    ) as pct_of_monthly_customers

from migrations
group by order_month, migration_status
