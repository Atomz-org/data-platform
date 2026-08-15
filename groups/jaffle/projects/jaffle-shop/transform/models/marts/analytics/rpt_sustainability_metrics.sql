with

waste_monthly as (

    select
        {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month,
        sum(quantity_wasted) as total_waste_quantity,
        sum(cost_of_waste) as total_waste_cost,
        count(waste_log_id) as waste_events,
        count(distinct waste_reason) as waste_reason_variety
    from {{ ref('stg_waste_logs') }}
    group by 1

),

waste_trend as (

    select
        waste_month,
        total_waste_quantity,
        total_waste_cost,
        waste_events,
        lag(total_waste_cost) over (order by waste_month) as prev_month_waste_cost,
        case
            when lag(total_waste_cost) over (order by waste_month) > 0
                then round(cast(
                    (total_waste_cost - lag(total_waste_cost) over (order by waste_month)) * 100.0
                    / lag(total_waste_cost) over (order by waste_month)
                as {{ dbt.type_float() }}), 2)
            else null
        end as waste_cost_mom_pct
    from waste_monthly

),

supplier_diversity as (

    select
        count(distinct supplier_id) as total_active_suppliers,
        count(distinct city) as supplier_cities,
        count(distinct state) as supplier_states
    from {{ ref('stg_suppliers') }}
    where is_active

),

final as (

    select
        wt.waste_month,
        wt.total_waste_quantity,
        wt.total_waste_cost,
        wt.waste_events,
        wt.waste_cost_mom_pct,
        sd.total_active_suppliers,
        sd.supplier_cities,
        sd.supplier_states
    from waste_trend as wt
    cross join supplier_diversity as sd

)

select * from final
