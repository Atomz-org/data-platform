with

supply_capacity as (
    select
        product_id,
        total_stock_on_hand,
        stocked_locations
    from {{ ref('int_supply_capacity') }}
),

product_sales as (
    select
        product_id,
        sum(units_sold) as total_demand
    from {{ ref('fct_product_sales') }}
    group by 1
),

products as (
    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}
),

final as (
    select
        p.product_id,
        p.product_name,
        p.product_type,
        coalesce(sc.total_stock_on_hand, 0) as current_supply,
        coalesce(ps.total_demand, 0) as total_demand,
        coalesce(sc.stocked_locations, 0) as supply_locations,
        coalesce(sc.total_stock_on_hand, 0) - coalesce(ps.total_demand, 0) as supply_demand_gap,
        case
            when coalesce(ps.total_demand, 0) > 0
            then coalesce(sc.total_stock_on_hand, 0) * 1.0 / ps.total_demand
            else null
        end as supply_demand_ratio,
        case
            when coalesce(sc.total_stock_on_hand, 0) = 0 then 'out_of_stock'
            when coalesce(sc.total_stock_on_hand, 0) < coalesce(ps.total_demand, 0) * 0.5 then 'critically_low'
            when coalesce(sc.total_stock_on_hand, 0) < coalesce(ps.total_demand, 0) then 'below_demand'
            else 'adequate'
        end as alignment_status
    from products as p
    left join supply_capacity as sc on p.product_id = sc.product_id
    left join product_sales as ps on p.product_id = ps.product_id
)

select * from final
