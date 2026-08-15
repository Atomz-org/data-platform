with

pricing_history as (

    select * from {{ ref('stg_pricing_history') }}

),

product_sales as (

    select
        product_id,
        sale_date,
        units_sold,
        daily_revenue
    from {{ ref('fct_product_sales') }}

),

-- Enrich price history with duration and volume
price_periods as (

    select
        ph.pricing_history_id,
        ph.product_id,
        ph.old_price,
        ph.new_price,
        ph.price_changed_date as period_start,
        coalesce(
            lead(ph.price_changed_date) over (
                partition by ph.product_id
                order by ph.price_changed_date
            ),
            current_date
        ) as period_end,
        {{ dbt.datediff(
            'ph.price_changed_date',
            "coalesce(lead(ph.price_changed_date) over (partition by ph.product_id order by ph.price_changed_date), current_date)",
            'day'
        ) }} as days_at_price
    from pricing_history as ph

),

-- Volume during each price period
volume_at_price as (

    select
        pp.pricing_history_id,
        pp.product_id,
        pp.new_price as price,
        pp.period_start,
        pp.period_end,
        pp.days_at_price,
        coalesce(sum(ps.units_sold), 0) as units_during_period,
        coalesce(sum(ps.daily_revenue), 0) as revenue_during_period,
        case
            when pp.days_at_price > 0
            then round(coalesce(sum(ps.units_sold), 0) * 1.0 / pp.days_at_price, 2)
            else 0
        end as avg_daily_units_at_price
    from price_periods as pp
    left join product_sales as ps
        on pp.product_id = ps.product_id
        and ps.sale_date >= pp.period_start
        and ps.sale_date < pp.period_end
    group by 1, 2, 3, 4, 5, 6

),

with_elasticity_inputs as (

    select
        vp.*,
        lag(vp.price) over (
            partition by vp.product_id
            order by vp.period_start
        ) as prior_price,
        lag(vp.avg_daily_units_at_price) over (
            partition by vp.product_id
            order by vp.period_start
        ) as prior_daily_units,
        case
            when lag(vp.price) over (partition by vp.product_id order by vp.period_start) > 0
                and lag(vp.avg_daily_units_at_price) over (partition by vp.product_id order by vp.period_start) > 0
            then round(
                ((vp.avg_daily_units_at_price - lag(vp.avg_daily_units_at_price) over (
                    partition by vp.product_id order by vp.period_start
                )) / lag(vp.avg_daily_units_at_price) over (
                    partition by vp.product_id order by vp.period_start
                ))
                /
                ((vp.price - lag(vp.price) over (
                    partition by vp.product_id order by vp.period_start
                )) / lag(vp.price) over (
                    partition by vp.product_id order by vp.period_start
                )), 4
            )
            else null
        end as point_elasticity_estimate
    from volume_at_price as vp

)

select * from with_elasticity_inputs
