with

product_margin_trend as (

    select * from {{ ref('int_product_margin_trend') }}

),

with_alerts as (

    select
        sale_month,
        product_id,
        product_name,
        product_type,
        monthly_units_sold,
        monthly_revenue,
        avg_selling_price,
        total_ingredient_cost,
        gross_margin,
        gross_margin_pct,
        monthly_gross_profit,
        prev_month_margin_pct,
        margin_pct_change,
        -- Detect consecutive declining months using a running count
        case
            when margin_pct_change < -5 then 'significant_decline'
            when margin_pct_change < -2 then 'moderate_decline'
            when margin_pct_change > 5 then 'significant_improvement'
            when margin_pct_change > 2 then 'moderate_improvement'
            else 'stable'
        end as margin_trend_status,
        case
            when gross_margin_pct < 30 then 'critical'
            when gross_margin_pct < 50 then 'warning'
            else 'healthy'
        end as margin_health,
        avg(gross_margin_pct) over (
            partition by product_id
            order by sale_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_margin_pct

    from product_margin_trend

)

select * from with_alerts
