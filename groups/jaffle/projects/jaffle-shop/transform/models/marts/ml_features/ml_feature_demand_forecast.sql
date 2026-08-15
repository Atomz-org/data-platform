with

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

date_spine as (

    select * from {{ ref('util_date_spine') }}

),

orders as (

    select
        order_id,
        location_id,
        ordered_at
    from {{ ref('stg_orders') }}

),

order_items as (

    select
        order_id,
        product_id
    from {{ ref('stg_order_items') }}

),

-- Product x store x week grain
product_store_week as (

    select
        oi.product_id,
        o.location_id as store_id,
        {{ dbt.date_trunc('week', 'o.ordered_at') }} as week_start,
        count(distinct oi.order_id) as weekly_orders,
        count(oi.product_id) as weekly_units
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    group by 1, 2, 3

),

-- Trailing features per product-store-week
with_trailing as (

    select
        product_id,
        store_id,
        week_start,
        weekly_orders,
        weekly_units,

        -- Trailing 4-week avg
        avg(weekly_units) over (
            partition by product_id, store_id
            order by week_start
            rows between 4 preceding and 1 preceding
        ) as trailing_4w_avg_units,

        -- Trailing 8-week avg
        avg(weekly_units) over (
            partition by product_id, store_id
            order by week_start
            rows between 8 preceding and 1 preceding
        ) as trailing_8w_avg_units,

        -- Same week last year (lag 52)
        lag(weekly_units, 52) over (
            partition by product_id, store_id
            order by week_start
        ) as same_week_prior_year_units,

        -- Seasonality index: ratio of current week to 8-week trailing
        case
            when avg(weekly_units) over (
                partition by product_id, store_id
                order by week_start
                rows between 8 preceding and 1 preceding
            ) > 0
            then round(
                (weekly_units * 1.0 / avg(weekly_units) over (
                    partition by product_id, store_id
                    order by week_start
                    rows between 8 preceding and 1 preceding
                )), 4
            )
            else null
        end as seasonality_index,

        -- Week-over-week growth
        lag(weekly_units, 1) over (
            partition by product_id, store_id
            order by week_start
        ) as prior_week_units

    from product_store_week

),

-- Add day-of-week pattern from date spine
week_metadata as (

    select distinct
        week_start,
        extract(month from week_start) as month_of_year
    from date_spine

),

final as (

    select
        wt.product_id,
        wt.store_id,
        wt.week_start,
        wm.month_of_year,
        wt.weekly_units,
        wt.weekly_orders,
        round(coalesce(wt.trailing_4w_avg_units, 0), 2) as trailing_4w_avg_units,
        round(coalesce(wt.trailing_8w_avg_units, 0), 2) as trailing_8w_avg_units,
        coalesce(wt.same_week_prior_year_units, 0) as same_week_prior_year_units,
        wt.seasonality_index,
        coalesce(wt.prior_week_units, 0) as prior_week_units
    from with_trailing as wt
    left join week_metadata as wm
        on wt.week_start = wm.week_start

)

select * from final
