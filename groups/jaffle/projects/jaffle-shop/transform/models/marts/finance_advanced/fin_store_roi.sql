with

store_pnl as (

    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        total_costs,
        net_profit
    from {{ ref('rpt_store_pnl') }}

),

store_info as (

    select
        location_id,
        opened_date,
        {{ dbt.datediff('opened_date', 'current_date', 'month') }} as months_open
    from {{ ref('stg_locations') }}

),

cumulative as (

    select
        sp.location_id,
        sp.store_name,
        sp.report_month,
        sp.monthly_revenue,
        sp.net_profit,
        si.opened_date,
        si.months_open,
        sum(sp.net_profit) over (
            partition by sp.location_id order by sp.report_month
        ) as cumulative_profit,
        sum(sp.monthly_revenue) over (
            partition by sp.location_id order by sp.report_month
        ) as cumulative_revenue
    from store_pnl as sp
    inner join store_info as si on sp.location_id = si.location_id

),

final as (

    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        net_profit,
        opened_date,
        months_open,
        cumulative_profit,
        cumulative_revenue,
        -- Estimate setup cost as 3x first month total costs
        first_value(net_profit) over (
            partition by location_id order by report_month
        ) * -3 as estimated_setup_cost,
        case
            when first_value(net_profit) over (partition by location_id order by report_month) * -3 != 0
            then cumulative_profit / abs(first_value(net_profit) over (
                partition by location_id order by report_month) * -3) * 100
            else null
        end as roi_pct
    from cumulative

)

select * from final
