with

waste as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month,
        sum(quantity_wasted) as total_waste_qty,
        sum(cost_of_waste) as total_cost_of_waste,
        count(*) as waste_events
    from {{ ref('fct_waste_events') }}
    group by 1, 2

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

sales as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'sale_date') }} as sale_month,
        sum(units_sold) as monthly_qty_sold,
        sum(daily_revenue) as monthly_revenue
    from {{ ref('fct_product_sales') }}
    group by 1, 2

),

final as (

    select
        w.product_id,
        p.product_name,
        p.product_type,
        w.waste_month,
        w.total_waste_qty,
        w.total_cost_of_waste,
        w.waste_events,
        coalesce(s.monthly_qty_sold, 0) as monthly_qty_sold,
        case
            when coalesce(s.monthly_qty_sold, 0) + w.total_waste_qty > 0
            then cast(w.total_waste_qty as {{ dbt.type_float() }})
                / (s.monthly_qty_sold + w.total_waste_qty) * 100
            else 0
        end as waste_rate_pct,
        case
            when coalesce(s.monthly_revenue, 0) > 0
            then w.total_cost_of_waste / s.monthly_revenue * 100
            else null
        end as cost_of_waste_pct_of_revenue
    from waste as w
    inner join products as p on w.product_id = p.product_id
    left join sales as s
        on w.product_id = s.product_id
        and w.waste_month = s.sale_month

)

select * from final
