with

cycle_times as (

    select * from {{ ref('int_procurement_cycle_time') }}

),

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

monthly_cycle_time as (

    select
        cycle_times.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'cycle_times.ordered_at') }} as order_month,
        count(cycle_times.purchase_order_id) as count_orders,
        avg(cycle_times.cycle_time_days) as avg_cycle_time_days,
        min(cycle_times.cycle_time_days) as min_cycle_time_days,
        max(cycle_times.cycle_time_days) as max_cycle_time_days,
        avg(cycle_times.expected_cycle_time_days) as avg_expected_cycle_time_days,
        avg(cycle_times.cycle_time_variance_days) as avg_cycle_time_variance_days,
        sum(
            case
                when cycle_times.cycle_time_variance_days <= 0 then 1
                else 0
            end
        ) as count_on_time_or_early,
        sum(
            case
                when cycle_times.cycle_time_variance_days > 0 then 1
                else 0
            end
        ) as count_late

    from cycle_times

    inner join suppliers
        on cycle_times.supplier_id = suppliers.supplier_id

    where cycle_times.cycle_time_days is not null

    group by
        cycle_times.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'cycle_times.ordered_at') }}

),

with_efficiency as (

    select
        *,
        case
            when count_orders > 0
                then count_on_time_or_early * 1.0 / count_orders
            else null
        end as on_time_rate,
        case
            when avg_expected_cycle_time_days > 0
                then avg_cycle_time_days / avg_expected_cycle_time_days
            else null
        end as cycle_time_efficiency_ratio

    from monthly_cycle_time

)

select * from with_efficiency
