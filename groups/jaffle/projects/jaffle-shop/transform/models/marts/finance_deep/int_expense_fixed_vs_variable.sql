with

expenses as (

    select * from {{ ref('stg_expenses') }}

),

expense_categories as (

    select * from {{ ref('stg_expense_categories') }}

),

orders as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(order_id) as order_count
    from {{ ref('stg_orders') }}
    group by 1, 2

),

monthly_expense as (

    select
        e.location_id,
        e.expense_category_id,
        ec.category_name,
        {{ dbt.date_trunc('month', 'e.incurred_date') }} as expense_month,
        sum(e.expense_amount) as monthly_expense
    from expenses as e
    left join expense_categories as ec
        on e.expense_category_id = ec.expense_category_id
    group by 1, 2, 3, 4

),

expense_with_volume as (

    select
        me.location_id,
        me.expense_category_id,
        me.category_name,
        me.expense_month,
        me.monthly_expense,
        coalesce(o.order_count, 0) as order_count,
        case
            when coalesce(o.order_count, 0) > 0
                then me.monthly_expense / o.order_count
            else null
        end as expense_per_order
    from monthly_expense as me
    left join orders as o
        on me.location_id = o.location_id
        and me.expense_month = o.order_month

),

category_variance as (

    select
        location_id,
        expense_category_id,
        category_name,
        avg(monthly_expense) as avg_monthly_expense,
        {{ dbt.safe_cast('stddev(monthly_expense)', dbt.type_float()) }} as stddev_expense,
        case
            when avg(monthly_expense) > 0
                then {{ dbt.safe_cast('stddev(monthly_expense)', dbt.type_float()) }} / avg(monthly_expense)
            else 0
        end as coefficient_of_variation,
        case
            when avg(monthly_expense) > 0
                and {{ dbt.safe_cast('stddev(monthly_expense)', dbt.type_float()) }} / avg(monthly_expense) < 0.15
                then 'fixed'
            else 'variable'
        end as expense_classification
    from expense_with_volume
    group by 1, 2, 3

)

select * from category_variance
