-- adv_cumulative_with_reset.sql
-- Technique: Running total with periodic reset using fiscal quarter partitioning
-- Computes a cumulative daily revenue that resets at the start of each fiscal
-- quarter. By partitioning the window function by fiscal_quarter + fiscal_year,
-- the running sum automatically resets at each quarter boundary. This pattern is
-- essential for fiscal reporting where YTD/QTD metrics must align to non-calendar
-- periods defined in util_fiscal_periods.

with fiscal_periods as (

    select * from {{ ref('util_fiscal_periods') }}

),

store_daily_revenue as (

    select * from {{ ref('int_revenue_by_store_daily') }}

),

-- Join daily revenue with fiscal periods to get quarter assignments
revenue_with_fiscal as (

    select
        sdr.revenue_date,
        sdr.location_id,
        sdr.location_name,
        sdr.total_revenue,
        sdr.invoice_count,
        fp.fiscal_year,
        fp.fiscal_quarter,
        fp.fiscal_month,
        -- Composite key for partitioning: fiscal year + quarter
        fp.fiscal_year || '-Q' || fp.fiscal_quarter as fiscal_quarter_label

    from store_daily_revenue as sdr
    inner join fiscal_periods as fp
        on sdr.revenue_date = fp.date_day

),

-- Cumulative sum partitioned by store + fiscal quarter (resets each quarter)
with_cumulative as (

    select
        revenue_date,
        location_id,
        location_name,
        fiscal_year,
        fiscal_quarter,
        fiscal_quarter_label,
        fiscal_month,
        total_revenue as daily_revenue,
        invoice_count,

        -- Running total that resets each fiscal quarter
        sum(total_revenue) over (
            partition by location_id, fiscal_year, fiscal_quarter
            order by revenue_date
            rows between unbounded preceding and current row
        ) as qtd_cumulative_revenue,

        -- Running order count that also resets each quarter
        sum(invoice_count) over (
            partition by location_id, fiscal_year, fiscal_quarter
            order by revenue_date
            rows between unbounded preceding and current row
        ) as qtd_cumulative_invoices,

        -- Day number within the fiscal quarter (for pacing analysis)
        row_number() over (
            partition by location_id, fiscal_year, fiscal_quarter
            order by revenue_date
        ) as day_of_quarter,

        -- Quarter-to-date average daily revenue
        avg(total_revenue) over (
            partition by location_id, fiscal_year, fiscal_quarter
            order by revenue_date
            rows between unbounded preceding and current row
        ) as qtd_avg_daily_revenue,

        -- For comparison: running total that does NOT reset (full cumulative)
        sum(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between unbounded preceding and current row
        ) as all_time_cumulative_revenue

    from revenue_with_fiscal

)

select
    revenue_date,
    location_id,
    location_name,
    fiscal_year,
    fiscal_quarter,
    fiscal_quarter_label,
    daily_revenue,
    invoice_count,
    day_of_quarter,
    round(qtd_cumulative_revenue, 2) as qtd_cumulative_revenue,
    qtd_cumulative_invoices,
    round(qtd_avg_daily_revenue, 2) as qtd_avg_daily_revenue,
    round(all_time_cumulative_revenue, 2) as all_time_cumulative_revenue
from with_cumulative
order by location_id, revenue_date
