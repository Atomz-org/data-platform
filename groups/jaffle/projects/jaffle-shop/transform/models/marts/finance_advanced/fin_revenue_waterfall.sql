with

monthly_orders as (

    select
        {{ dbt.date_trunc('month', 'ordered_at') }} as revenue_month,
        customer_id,
        sum(order_total) as customer_revenue
    from {{ ref('stg_orders') }}
    group by 1, 2

),

customer_first_month as (

    select
        customer_id,
        min(revenue_month) as first_month
    from monthly_orders
    group by 1

),

classified as (

    select
        mo.revenue_month,
        mo.customer_id,
        mo.customer_revenue,
        cfm.first_month,
        case
            when mo.revenue_month = cfm.first_month then 'new_customer'
            else 'returning_customer'
        end as customer_type,
        lag(mo.customer_revenue) over (
            partition by mo.customer_id order by mo.revenue_month
        ) as prev_month_revenue
    from monthly_orders as mo
    inner join customer_first_month as cfm
        on mo.customer_id = cfm.customer_id

),

waterfall as (

    select
        revenue_month,
        sum(case when customer_type = 'new_customer' then customer_revenue else 0 end) as new_customer_revenue,
        sum(case when customer_type = 'returning_customer' and prev_month_revenue is not null
                      and customer_revenue > prev_month_revenue
                 then customer_revenue - prev_month_revenue else 0 end) as upsell_revenue,
        sum(case when customer_type = 'returning_customer' and prev_month_revenue is not null
                      and customer_revenue <= prev_month_revenue
                 then customer_revenue else 0 end) as stable_returning_revenue,
        sum(case when customer_type = 'returning_customer' and prev_month_revenue is not null
                      and customer_revenue < prev_month_revenue
                 then prev_month_revenue - customer_revenue else 0 end) as downsell_amount,
        sum(customer_revenue) as total_revenue
    from classified
    group by 1

),

with_churn as (

    select
        w.revenue_month,
        w.new_customer_revenue,
        w.upsell_revenue,
        w.stable_returning_revenue,
        w.downsell_amount,
        coalesce(lag(w.total_revenue) over (order by w.revenue_month), 0) as opening_balance,
        w.total_revenue as closing_balance
    from waterfall as w

)

select
    revenue_month,
    opening_balance,
    new_customer_revenue,
    upsell_revenue,
    stable_returning_revenue,
    -1 * downsell_amount as downsell_impact,
    opening_balance - closing_balance + new_customer_revenue + upsell_revenue - downsell_amount
        - stable_returning_revenue as implied_churn_revenue,
    closing_balance
from with_churn
