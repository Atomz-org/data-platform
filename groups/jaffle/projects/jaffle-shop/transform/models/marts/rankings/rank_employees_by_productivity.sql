with

employee_prod as (
    select
        employee_id,
        avg(avg_orders_per_hour) as avg_productivity,
        count(distinct metric_month) as months_measured
    from {{ ref('int_employee_monthly_metrics') }}
    group by 1
),

ranked as (
    select
        employee_id,
        avg_productivity,
        months_measured,
        rank() over (order by avg_productivity desc) as productivity_rank,
        ntile(4) over (order by avg_productivity desc) as productivity_quartile
    from employee_prod
    where months_measured >= 2
)

select * from ranked
