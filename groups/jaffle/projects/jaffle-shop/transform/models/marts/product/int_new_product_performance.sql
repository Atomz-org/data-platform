with

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

pricing_changes as (

    select * from {{ ref('fct_pricing_changes') }}

),

product_launch_date as (

    select
        product_id,
        product_name,
        min(price_changed_date) as launch_date

    from pricing_changes
    group by product_id, product_name

),

sales_with_launch as (

    select
        ps.sale_date,
        ps.product_id,
        ps.product_name,
        ps.product_type,
        ps.units_sold,
        ps.daily_revenue,
        pld.launch_date,
        {{ dbt.datediff('pld.launch_date', 'ps.sale_date', 'day') }} as days_since_launch

    from product_sales as ps
    inner join product_launch_date as pld
        on ps.product_id = pld.product_id
    where ps.sale_date >= pld.launch_date

),

performance_windows as (

    select
        product_id,
        product_name,
        product_type,
        launch_date,
        -- First 30 days
        sum(case when days_since_launch <= 30 then units_sold else 0 end) as units_sold_30d,
        sum(case when days_since_launch <= 30 then daily_revenue else 0 end) as revenue_30d,
        count(distinct case when days_since_launch <= 30 then sale_date end) as active_days_30d,
        -- First 60 days
        sum(case when days_since_launch <= 60 then units_sold else 0 end) as units_sold_60d,
        sum(case when days_since_launch <= 60 then daily_revenue else 0 end) as revenue_60d,
        count(distinct case when days_since_launch <= 60 then sale_date end) as active_days_60d,
        -- First 90 days
        sum(case when days_since_launch <= 90 then units_sold else 0 end) as units_sold_90d,
        sum(case when days_since_launch <= 90 then daily_revenue else 0 end) as revenue_90d,
        count(distinct case when days_since_launch <= 90 then sale_date end) as active_days_90d,
        -- Overall
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        max(days_since_launch) as days_on_market

    from sales_with_launch
    group by product_id, product_name, product_type, launch_date

),

final as (

    select
        *,
        case
            when active_days_30d > 0
            then units_sold_30d * 1.0 / active_days_30d
            else 0
        end as avg_daily_units_30d,
        case
            when active_days_60d > 0
            then units_sold_60d * 1.0 / active_days_60d
            else 0
        end as avg_daily_units_60d,
        case
            when active_days_90d > 0
            then units_sold_90d * 1.0 / active_days_90d
            else 0
        end as avg_daily_units_90d

    from performance_windows

)

select * from final
