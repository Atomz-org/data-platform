with

delivery_data as (
    select
        cast(actual_arrival_at as date) as delivery_date,
        supplier_id,
        actual_transit_days as lead_time_days
    from {{ ref('fct_deliveries') }}
    where actual_arrival_at is not null
),

daily_supplier as (
    select
        delivery_date,
        supplier_id,
        avg(lead_time_days) as avg_lead_time,
        count(*) as delivery_count
    from delivery_data
    group by 1, 2
),

trended as (
    select
        delivery_date,
        supplier_id,
        avg_lead_time,
        delivery_count,
        avg(avg_lead_time) over (
            partition by supplier_id order by delivery_date
            rows between 6 preceding and current row
        ) as lead_time_7d_ma,
        avg(avg_lead_time) over (
            partition by supplier_id order by delivery_date
            rows between 27 preceding and current row
        ) as lead_time_28d_ma,
        case
            when avg_lead_time > avg(avg_lead_time) over (
                partition by supplier_id order by delivery_date
                rows between 27 preceding and current row
            ) * 1.2 then 'deteriorating'
            when avg_lead_time < avg(avg_lead_time) over (
                partition by supplier_id order by delivery_date
                rows between 27 preceding and current row
            ) * 0.8 then 'improving'
            else 'stable'
        end as trend_direction
    from daily_supplier
)

select * from trended
