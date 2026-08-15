with store_data as (
    select
        store_id,
        store_name,
        total_revenue,
        total_expenses,
        total_labor_cost,
        total_net_income,
        avg_operating_margin_pct,
        avg_labor_cost_pct,
        total_inventory_value,
        total_marketing_spend,
        avg_employee_count,
        months_of_data
    from {{ ref('dim_store_profile') }}
),

fleet_averages as (
    select
        avg(total_revenue) as fleet_avg_revenue,
        avg(total_net_income) as fleet_avg_net_income,
        avg(avg_operating_margin_pct) as fleet_avg_margin,
        avg(avg_labor_cost_pct) as fleet_avg_labor_pct,
        avg(total_inventory_value) as fleet_avg_inventory_value,
        avg(total_marketing_spend) as fleet_avg_marketing_spend,
        avg(avg_employee_count) as fleet_avg_employees,
        stddev(avg_operating_margin_pct) as fleet_stddev_margin,
        stddev(avg_labor_cost_pct) as fleet_stddev_labor_pct
    from store_data
),

revenue_per_employee as (
    select
        store_id,
        case
            when avg_employee_count > 0
                then round(cast(total_revenue as {{ dbt.type_float() }}) / avg_employee_count, 2)
            else 0
        end as revenue_per_employee
    from store_data
)

select
    sd.store_id,
    sd.store_name,
    sd.total_revenue,
    round(cast(fa.fleet_avg_revenue as {{ dbt.type_float() }}), 2) as fleet_avg_revenue,
    round(cast(sd.total_revenue - fa.fleet_avg_revenue as {{ dbt.type_float() }}), 2) as revenue_vs_fleet,

    sd.avg_operating_margin_pct,
    round(cast(fa.fleet_avg_margin as {{ dbt.type_float() }}), 2) as fleet_avg_margin,
    round(cast(sd.avg_operating_margin_pct - fa.fleet_avg_margin as {{ dbt.type_float() }}), 2) as margin_vs_fleet,

    sd.avg_labor_cost_pct,
    round(cast(fa.fleet_avg_labor_pct as {{ dbt.type_float() }}), 2) as fleet_avg_labor_pct,
    round(cast(sd.avg_labor_cost_pct - fa.fleet_avg_labor_pct as {{ dbt.type_float() }}), 2) as labor_pct_vs_fleet,

    rpe.revenue_per_employee,
    round(cast(
        fa.fleet_avg_revenue / nullif(fa.fleet_avg_employees, 0) as {{ dbt.type_float() }}
    ), 2) as fleet_avg_revenue_per_employee,

    -- Performance flags
    case
        when sd.avg_operating_margin_pct > fa.fleet_avg_margin + fa.fleet_stddev_margin
            then 'above_average'
        when sd.avg_operating_margin_pct < fa.fleet_avg_margin - fa.fleet_stddev_margin
            then 'below_average'
        else 'average'
    end as margin_performance,

    case
        when sd.avg_labor_cost_pct > fa.fleet_avg_labor_pct + fa.fleet_stddev_labor_pct
            then 'high_labor_cost'
        when sd.avg_labor_cost_pct < fa.fleet_avg_labor_pct - fa.fleet_stddev_labor_pct
            then 'low_labor_cost'
        else 'average_labor_cost'
    end as labor_cost_flag,

    rank() over (order by sd.total_revenue desc) as revenue_rank,
    rank() over (order by sd.avg_operating_margin_pct desc) as margin_rank

from store_data as sd
cross join fleet_averages as fa
left join revenue_per_employee as rpe
    on sd.store_id = rpe.store_id
