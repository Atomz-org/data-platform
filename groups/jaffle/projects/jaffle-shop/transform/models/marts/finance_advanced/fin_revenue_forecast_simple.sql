with

monthly_rev as (

    select
        location_id,
        store_name,
        month_start,
        monthly_revenue,
        row_number() over (partition by location_id order by month_start) as month_seq
    from {{ ref('met_monthly_revenue_by_store') }}

),

store_stats as (

    select
        location_id,
        store_name,
        count(*) as n_months,
        avg(monthly_revenue) as avg_revenue,
        -- Simple linear regression: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - (sum(x))^2)
        (count(*) * sum(month_seq * monthly_revenue) - sum(month_seq) * sum(monthly_revenue))
            / nullif(count(*) * sum(month_seq * month_seq) - sum(month_seq) * sum(month_seq), 0) as slope,
        max(month_seq) as last_seq,
        max(month_start) as last_month
    from monthly_rev
    group by 1, 2

),

with_intercept as (

    select
        location_id,
        store_name,
        n_months,
        avg_revenue,
        slope,
        last_seq,
        last_month,
        avg_revenue - slope * (cast(n_months + 1 as {{ dbt.type_float() }}) / 2) as intercept
    from store_stats

),

forecast as (

    select
        location_id,
        store_name,
        n_months,
        avg_revenue,
        slope,
        intercept,
        last_month,
        -- Forecast next 3 months
        {{ sf_greatest(["(intercept + slope * (last_seq + 1))", "0"]) }} as forecast_month_1,
        {{ sf_greatest(["(intercept + slope * (last_seq + 2))", "0"]) }} as forecast_month_2,
        {{ sf_greatest(["(intercept + slope * (last_seq + 3))", "0"]) }} as forecast_month_3,
        case
            when avg_revenue > 0
            then slope / avg_revenue * 100
            else 0
        end as monthly_growth_rate_pct
    from with_intercept

)

select * from forecast
