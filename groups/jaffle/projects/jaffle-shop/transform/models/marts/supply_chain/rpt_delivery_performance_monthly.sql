with

delivery_tracking as (

    select * from {{ ref('int_delivery_tracking') }}

),

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

monthly_performance as (

    select
        delivery_tracking.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'delivery_tracking.shipped_at') }} as delivery_month,
        count(delivery_tracking.shipment_id) as total_shipments,
        -- NOTE: simplified on-time calculation
        sum(
            case when delivery_tracking.is_on_time is not null then 1 else 0 end
        ) as on_time_shipments,
        sum(
            case when delivery_tracking.is_on_time = false then 1 else 0 end
        ) as late_shipments,
        sum(
            case when delivery_tracking.is_on_time is null then 1 else 0 end
        ) as pending_shipments,
        avg(delivery_tracking.actual_transit_days) as avg_transit_days,
        avg(delivery_tracking.expected_transit_days) as avg_expected_transit_days,
        case
            when count(
                case when delivery_tracking.is_on_time is not null then 1 end
            ) > 0
                then sum(
                    case when delivery_tracking.is_on_time = true then 1 else 0 end
                ) * 1.0 / count(
                    case when delivery_tracking.is_on_time is not null then 1 end
                )
            else null
        end as monthly_on_time_rate

    from delivery_tracking

    inner join suppliers
        on delivery_tracking.supplier_id = suppliers.supplier_id

    group by
        delivery_tracking.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'delivery_tracking.shipped_at') }}

)

select * from monthly_performance
