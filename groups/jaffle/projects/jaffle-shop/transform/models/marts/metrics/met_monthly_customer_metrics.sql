with

monthly_active as (

    select * from {{ ref('int_monthly_active_customers') }}

),

customer_status as (

    select * from {{ ref('int_customer_status_monthly') }}

),

status_counts as (

    select
        month_start,
        count(distinct customer_id) as total_tracked_customers,
        count(distinct case when customer_status = 'active' then customer_id end) as active_customers,
        count(distinct case when customer_status = 'dormant' then customer_id end) as dormant_customers,
        count(distinct case when customer_status = 'churned' then customer_id end) as churned_customers

    from customer_status
    group by 1

),

final as (

    select
        ma.month_start,
        ma.total_customer_visits,
        ma.total_orders,
        ma.total_revenue,
        ma.new_customers,
        ma.returning_customer_visits,
        ma.avg_daily_customers,
        ma.mom_customer_visit_change,
        ma.mom_new_customer_change,
        coalesce(sc.total_tracked_customers, 0) as total_tracked_customers,
        coalesce(sc.active_customers, 0) as tracked_active_customers,
        coalesce(sc.dormant_customers, 0) as dormant_customers,
        coalesce(sc.churned_customers, 0) as churned_customers,
        case
            when coalesce(sc.total_tracked_customers, 0) > 0
            then sc.active_customers * 100.0 / sc.total_tracked_customers
            else 0
        end as active_pct,
        case
            when coalesce(sc.total_tracked_customers, 0) > 0
            then sc.churned_customers * 100.0 / sc.total_tracked_customers
            else 0
        end as churn_pct

    from monthly_active as ma

    left join status_counts as sc
        on ma.month_start = sc.month_start

)

select * from final
