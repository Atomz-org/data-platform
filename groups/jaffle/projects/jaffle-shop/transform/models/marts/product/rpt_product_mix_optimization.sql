with

product_sales as (

    select
        product_id,
        product_name,
        product_type,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        count(distinct sale_date) as active_sale_days,
        avg(units_sold) as avg_daily_units

    from {{ ref('int_product_sales_daily') }}
    group by product_id, product_name, product_type

),

product_affinity as (

    select * from {{ ref('int_product_affinity') }}

),

top_affinities as (

    select
        product_id_a as product_id,
        product_id_b as top_paired_product_id,
        co_occurrence_count as top_pair_co_occurrences,
        support_a as top_pair_support

    from product_affinity
    where affinity_rank = 1

),

products_ranked as (

    select
        ps.product_id,
        ps.product_name,
        ps.product_type,
        ps.total_units_sold,
        ps.total_revenue,
        ps.active_sale_days,
        ps.avg_daily_units,
        ps.total_revenue * 1.0
            / nullif(sum(ps.total_revenue) over (), 0) as revenue_contribution_pct,
        rank() over (order by ps.total_revenue desc) as revenue_rank,
        rank() over (order by ps.total_units_sold desc) as volume_rank,
        ta.top_paired_product_id,
        ta.top_pair_co_occurrences,
        ta.top_pair_support

    from product_sales as ps
    left join top_affinities as ta
        on ps.product_id = ta.product_id

),

final as (

    select
        product_id,
        product_name,
        product_type,
        total_units_sold,
        total_revenue,
        active_sale_days,
        avg_daily_units,
        revenue_contribution_pct,
        revenue_rank,
        volume_rank,
        top_paired_product_id,
        top_pair_co_occurrences,
        top_pair_support,
        case
            when revenue_rank <= 5 and volume_rank <= 5 then 'star'
            when revenue_rank <= 10 then 'strong_performer'
            when volume_rank <= 10 then 'volume_driver'
            else 'underperformer'
        end as product_classification

    from products_ranked

)

select * from final
