with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

monthly_orders as (

    select * from {{ ref('int_monthly_orders_by_store') }}

),

-- Store-level features per month
store_monthly_features as (

    select
        mo.location_id as store_id,
        mo.month_start,
        mo.total_revenue as monthly_revenue,
        mo.order_count as monthly_orders,
        mo.unique_customer_visits as monthly_customers,
        mo.active_days_in_month,

        -- Trailing revenue features
        avg(mo.total_revenue) over (
            partition by mo.location_id
            order by mo.month_start
            rows between 3 preceding and 1 preceding
        ) as trailing_3m_avg_revenue,

        avg(mo.total_revenue) over (
            partition by mo.location_id
            order by mo.month_start
            rows between 6 preceding and 1 preceding
        ) as trailing_6m_avg_revenue,

        -- Prior month
        lag(mo.total_revenue, 1) over (
            partition by mo.location_id
            order by mo.month_start
        ) as prior_month_revenue,

        -- Same month last year
        lag(mo.total_revenue, 12) over (
            partition by mo.location_id
            order by mo.month_start
        ) as same_month_prior_year,

        -- Month-over-month growth
        mo.mom_revenue_growth,

        -- Seasonality proxy: month number
        extract(month from mo.month_start) as month_of_year

    from monthly_orders as mo

),

final as (

    select
        smf.store_id,
        sp.store_name,
        smf.month_start,
        smf.monthly_revenue,
        smf.monthly_orders,
        smf.monthly_customers,
        smf.active_days_in_month,
        round(coalesce(smf.trailing_3m_avg_revenue, 0), 2) as trailing_3m_avg_revenue,
        round(coalesce(smf.trailing_6m_avg_revenue, 0), 2) as trailing_6m_avg_revenue,
        coalesce(smf.prior_month_revenue, 0) as prior_month_revenue,
        coalesce(smf.same_month_prior_year, 0) as same_month_prior_year,
        coalesce(smf.mom_revenue_growth, 0) as mom_revenue_growth,
        smf.month_of_year,

        -- Store structural features
        sp.avg_employee_count as staff_count,
        sp.avg_labor_cost_pct as labor_cost_pct,
        sp.total_marketing_spend,
        sp.avg_operating_margin_pct as operating_margin_pct
    from store_monthly_features as smf
    inner join store_profile as sp
        on smf.store_id = sp.store_id

)

select * from final
