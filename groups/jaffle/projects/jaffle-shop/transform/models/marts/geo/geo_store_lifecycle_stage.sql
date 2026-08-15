with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

store_trends as (

    select
        location_id,
        count(distinct month_start) as months_of_data,
        avg(monthly_revenue) as avg_revenue,
        -- Compare recent 3 months to prior 3 months
        avg(case
            when month_start >= (select max(month_start) - interval '3 months' from monthly_revenue)
            then monthly_revenue
        end) as recent_avg,
        avg(case
            when month_start >= (select max(month_start) - interval '6 months' from monthly_revenue)
                and month_start < (select max(month_start) - interval '3 months' from monthly_revenue)
            then monthly_revenue
        end) as prior_avg

    from monthly_revenue
    group by location_id

),

classified as (

    select
        sp.location_id,
        sp.store_name,
        st.months_of_data,
        round(st.avg_revenue, 2) as avg_revenue,
        round(st.recent_avg, 2) as recent_3m_avg,
        round(st.prior_avg, 2) as prior_3m_avg,
        round(
            (st.recent_avg - st.prior_avg) * 100.0 / nullif(st.prior_avg, 0), 2
        ) as growth_pct,
        case
            when st.months_of_data <= 6 then 'new'
            when (st.recent_avg - st.prior_avg) * 100.0 / nullif(st.prior_avg, 0) > 5 then 'growing'
            when (st.recent_avg - st.prior_avg) * 100.0 / nullif(st.prior_avg, 0) >= -5 then 'mature'
            else 'declining'
        end as lifecycle_stage

    from store_profile sp
    left join store_trends st on sp.location_id = st.location_id

)

select * from classified
