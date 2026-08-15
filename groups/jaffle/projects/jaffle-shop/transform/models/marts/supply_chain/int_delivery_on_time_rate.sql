with

delivery_tracking as (

    select * from {{ ref('int_delivery_tracking') }}

),

supplier_delivery_stats as (

    select
        supplier_id,
        count(shipment_id) as total_deliveries,
        sum(
            case when is_on_time = true then 1 else 0 end
        ) as on_time_deliveries,
        sum(
            case when is_on_time = false then 1 else 0 end
        ) as late_deliveries,
        sum(
            case when is_on_time is null then 1 else 0 end
        ) as pending_deliveries,
        avg(actual_transit_days) as avg_transit_days,
        avg(expected_transit_days) as avg_expected_transit_days,
        case
            when count(
                case when is_on_time is not null then 1 end
            ) > 0
                then sum(
                    case when is_on_time = true then 1 else 0 end
                ) * 1.0 / count(
                    case when is_on_time is not null then 1 end
                )
            else null
        end as on_time_rate

    from delivery_tracking

    group by supplier_id

)

select * from supplier_delivery_stats
