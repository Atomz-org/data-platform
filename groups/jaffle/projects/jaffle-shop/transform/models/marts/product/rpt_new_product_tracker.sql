with

new_product_performance as (

    select * from {{ ref('int_new_product_performance') }}

),

-- Calculate overall averages for benchmarking
product_benchmarks as (

    select
        avg(avg_daily_units_30d) as benchmark_avg_daily_units_30d,
        avg(avg_daily_units_60d) as benchmark_avg_daily_units_60d,
        avg(avg_daily_units_90d) as benchmark_avg_daily_units_90d,
        avg(revenue_30d) as benchmark_revenue_30d,
        avg(revenue_60d) as benchmark_revenue_60d,
        avg(revenue_90d) as benchmark_revenue_90d

    from new_product_performance

),

final as (

    select
        npp.product_id,
        npp.product_name,
        npp.product_type,
        npp.launch_date,
        npp.days_on_market,
        npp.units_sold_30d,
        npp.revenue_30d,
        npp.avg_daily_units_30d,
        npp.units_sold_60d,
        npp.revenue_60d,
        npp.avg_daily_units_60d,
        npp.units_sold_90d,
        npp.revenue_90d,
        npp.avg_daily_units_90d,
        npp.total_units_sold,
        npp.total_revenue,
        -- Performance vs benchmark
        case
            when pb.benchmark_avg_daily_units_30d > 0
            then (npp.avg_daily_units_30d - pb.benchmark_avg_daily_units_30d)
                 / pb.benchmark_avg_daily_units_30d * 100
            else null
        end as pct_vs_benchmark_30d,
        case
            when pb.benchmark_avg_daily_units_90d > 0
            then (npp.avg_daily_units_90d - pb.benchmark_avg_daily_units_90d)
                 / pb.benchmark_avg_daily_units_90d * 100
            else null
        end as pct_vs_benchmark_90d,
        -- Trajectory: is the product accelerating or decelerating?
        -- NOTE: velocity change shows acceleration trend
        case
            when npp.avg_daily_units_30d > 0 and npp.active_days_60d > 30
            then (npp.avg_daily_units_30d - npp.avg_daily_units_60d)
                 / npp.avg_daily_units_30d * 100
            else null
        end as velocity_change_30_to_60d,
        -- Launch performance classification
        case
            when npp.avg_daily_units_30d >= pb.benchmark_avg_daily_units_30d * 1.5
            then 'strong_launch'
            when npp.avg_daily_units_30d >= pb.benchmark_avg_daily_units_30d
            then 'on_track'
            when npp.avg_daily_units_30d >= pb.benchmark_avg_daily_units_30d * 0.5
            then 'below_expectations'
            else 'underperforming'
        end as launch_classification

    from new_product_performance as npp
    cross join product_benchmarks as pb

)

select * from final
