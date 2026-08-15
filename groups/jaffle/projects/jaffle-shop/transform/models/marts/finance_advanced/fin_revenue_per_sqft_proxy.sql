with

monthly_rev as (

    select
        location_id,
        store_name,
        month_start,
        monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}

),

store_age as (

    select
        location_id,
        location_name,
        opened_date,
        {{ dbt.datediff('opened_date', 'current_date', 'month') }} as months_open
    from {{ ref('stg_locations') }}

),

final as (

    select
        mr.location_id,
        mr.store_name,
        mr.month_start,
        mr.monthly_revenue,
        sa.opened_date,
        sa.months_open,
        -- Use store age as proxy for size (older stores tend to be larger)
        case
            when sa.months_open > 60 then 1.5
            when sa.months_open > 36 then 1.2
            when sa.months_open > 12 then 1.0
            else 0.8
        end as size_proxy_factor,
        mr.monthly_revenue / nullif(
            case
                when sa.months_open > 60 then 1.5
                when sa.months_open > 36 then 1.2
                when sa.months_open > 12 then 1.0
                else 0.8
            end, 0
        ) as normalized_revenue
    from monthly_rev as mr
    inner join store_age as sa
        on mr.location_id = sa.location_id

)

select * from final
