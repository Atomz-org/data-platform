with

depletion as (

    select
        product_id,
        location_id,
        daily_depletion_rate
    from {{ ref('int_stock_depletion_rate') }}

),

lead_times as (

    select
        supplier_id,
        avg_lead_time_days,
        avg_lead_time_variance_days
    from {{ ref('int_lead_time_by_supplier') }}

),

inventory as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

-- Use average lead time across suppliers as proxy
avg_lead as (

    select
        avg(avg_lead_time_days) as global_avg_lead_time,
        avg(coalesce(avg_lead_time_variance_days, 0)) as global_lead_time_std
    from lead_times

),

final as (

    select
        d.product_id,
        d.location_id,
        d.daily_depletion_rate,
        inv.current_quantity,
        al.global_avg_lead_time,
        al.global_lead_time_std,
        -- Safety stock = Z * sqrt(LT * demand_variance + demand_avg^2 * LT_variance)
        -- Using Z=1.65 for 95% service level
        1.65 * sqrt(
            al.global_avg_lead_time * power(coalesce(d.daily_depletion_rate, 0), 2)
            + power(d.daily_depletion_rate, 2) * power(coalesce(al.global_lead_time_std, 0), 2)
        ) as safety_stock_units,
        d.daily_depletion_rate * al.global_avg_lead_time as reorder_demand,
        inv.current_quantity - d.daily_depletion_rate * al.global_avg_lead_time as excess_or_deficit
    from depletion as d
    cross join avg_lead as al
    left join inventory as inv
        on d.product_id = inv.product_id
        and d.location_id = inv.location_id

)

select * from final
