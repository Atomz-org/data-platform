with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

rc as (
    select * from {{ ref('fct_recipe_costs') }}
),

monthly_margin as (
    select
        {{ sf_date_trunc('month', "ps.sale_date") }} as sale_month,
        round((sum(ps.daily_revenue) - sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0))) * 100.0
            / nullif(sum(ps.daily_revenue), 0), 2) as gross_margin_pct
    from ps
    left join rc on ps.product_id = rc.menu_item_id
    group by 1
),

trended as (
    select
        sale_month,
        gross_margin_pct,
        avg(gross_margin_pct) over (order by sale_month rows between 3 preceding and 1 preceding) as margin_3m_avg,
        lag(gross_margin_pct) over (order by sale_month) as prior_month_margin
    from monthly_margin
),

alerts as (
    select
        sale_month,
        gross_margin_pct,
        margin_3m_avg,
        gross_margin_pct - margin_3m_avg as margin_vs_avg,
        'margin_erosion' as alert_type,
        case when gross_margin_pct < margin_3m_avg - 10 then 'critical' else 'warning' end as severity
    from trended
    where gross_margin_pct < margin_3m_avg - 5
      and margin_3m_avg > 0
)

select * from alerts
