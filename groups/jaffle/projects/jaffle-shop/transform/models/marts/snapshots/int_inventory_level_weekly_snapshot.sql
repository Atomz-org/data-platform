with

inventory_movements as (

    select * from {{ ref('fct_inventory_movements') }}

),

-- Generate week-end dates from movement data
week_ends as (

    select distinct
        {{ dbt.date_trunc('week', 'moved_at') }} + interval '6 days' as week_end_date

    from inventory_movements

),

-- Cumulative inventory per product per location up to each week end
weekly_balances as (

    select
        we.week_end_date,
        im.product_id,
        im.product_name,
        im.location_id,
        im.location_name,
        sum(im.quantity) as end_of_week_balance,
        sum(
            case when im.is_inbound then im.absolute_quantity else 0 end
        ) as weekly_inbound,
        sum(
            case when im.is_outbound then im.absolute_quantity else 0 end
        ) as weekly_outbound,
        count(im.movement_id) as movement_count

    from week_ends as we

    inner join inventory_movements as im
        on im.moved_at <= we.week_end_date

    group by 1, 2, 3, 4, 5

)

select * from weekly_balances
