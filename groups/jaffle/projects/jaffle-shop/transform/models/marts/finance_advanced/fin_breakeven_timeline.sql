with

store_pnl as (

    select
        location_id,
        store_name,
        report_month,
        net_profit,
        sum(net_profit) over (
            partition by location_id order by report_month
        ) as cumulative_profit,
        row_number() over (
            partition by location_id order by report_month
        ) as month_number
    from {{ ref('rpt_store_pnl') }}

),

store_info as (

    select
        location_id,
        opened_date
    from {{ ref('stg_locations') }}

),

breakeven_month as (

    select
        location_id,
        store_name,
        min(case when cumulative_profit >= 0 then month_number else null end) as months_to_breakeven,
        min(case when cumulative_profit >= 0 then report_month else null end) as breakeven_date
    from store_pnl
    group by 1, 2

),

latest_status as (

    select
        location_id,
        max(cumulative_profit) as latest_cumulative_profit,
        max(month_number) as total_months
    from store_pnl
    group by 1

),

final as (

    select
        bm.location_id,
        bm.store_name,
        si.opened_date,
        bm.months_to_breakeven,
        bm.breakeven_date,
        ls.latest_cumulative_profit,
        ls.total_months,
        case
            when bm.breakeven_date is not null then 'breakeven_achieved'
            when ls.latest_cumulative_profit > 0 then 'profitable_recently'
            else 'not_yet_breakeven'
        end as breakeven_status,
        case
            when bm.months_to_breakeven is null and ls.total_months > 0
            then -1 * ls.latest_cumulative_profit
                / nullif(ls.latest_cumulative_profit / ls.total_months, 0)
                + ls.total_months
            else null
        end as estimated_months_to_breakeven
    from breakeven_month as bm
    inner join store_info as si on bm.location_id = si.location_id
    inner join latest_status as ls on bm.location_id = ls.location_id

)

select * from final
