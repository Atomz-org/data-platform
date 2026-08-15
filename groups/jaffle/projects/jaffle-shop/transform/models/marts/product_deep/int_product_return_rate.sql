with

waste_events as (

    select
        product_id,
        sum(quantity_wasted) as total_wasted,
        sum(cost_of_waste) as total_waste_cost
    from {{ ref('stg_waste_logs') }}
    group by 1

),

product_sales as (

    select
        product_id,
        sum(units_sold) as total_sold,
        sum(daily_revenue) as total_revenue
    from {{ ref('fct_product_sales') }}
    group by 1

),

final as (

    select
        ps.product_id,
        ps.total_sold,
        ps.total_revenue,
        coalesce(we.total_wasted, 0) as total_wasted,
        coalesce(we.total_waste_cost, 0) as total_waste_cost,
        case
            when ps.total_sold > 0
                then round(cast(coalesce(we.total_wasted, 0) as {{ dbt.type_float() }}) * 100.0 / ps.total_sold, 2)
            else 0
        end as waste_rate_pct,
        case
            when ps.total_revenue > 0
                then round(cast(coalesce(we.total_waste_cost, 0) as {{ dbt.type_float() }}) * 100.0 / ps.total_revenue, 2)
            else 0
        end as waste_cost_as_pct_of_revenue
    from product_sales as ps
    left join waste_events as we
        on ps.product_id = we.product_id

)

select * from final
