with

pricing_changes as (

    select * from {{ ref('fct_pricing_changes') }}

),

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

-- 14 days before and after for tighter signal
pre_change as (

    select
        pc.pricing_history_id,
        pc.product_id,
        sum(ps.units_sold) as total_units_before,
        sum(ps.daily_revenue) as total_revenue_before,
        avg(ps.units_sold) as avg_daily_units_before,
        avg(ps.daily_revenue) as avg_daily_revenue_before,
        count(distinct ps.sale_date) as days_with_sales_before

    from pricing_changes as pc
    inner join product_sales as ps
        on pc.product_id = ps.product_id
        and ps.sale_date >= {{ dbt.dateadd('day', -14, 'pc.price_changed_date') }}
        and ps.sale_date < pc.price_changed_date
    group by pc.pricing_history_id, pc.product_id

),

post_change as (

    select
        pc.pricing_history_id,
        pc.product_id,
        sum(ps.units_sold) as total_units_after,
        sum(ps.daily_revenue) as total_revenue_after,
        avg(ps.units_sold) as avg_daily_units_after,
        avg(ps.daily_revenue) as avg_daily_revenue_after,
        count(distinct ps.sale_date) as days_with_sales_after

    from pricing_changes as pc
    inner join product_sales as ps
        on pc.product_id = ps.product_id
        and ps.sale_date >= pc.price_changed_date
        and ps.sale_date < {{ dbt.dateadd('day', 14, 'pc.price_changed_date') }}
    group by pc.pricing_history_id, pc.product_id

),

final as (

    select
        pc.pricing_history_id,
        pc.product_id,
        pc.product_name,
        pc.product_type,
        pc.old_price,
        pc.new_price,
        pc.price_change_amount,
        pc.price_change_pct,
        pc.price_change_direction,
        pc.change_reason,
        pc.price_changed_date,
        pre.avg_daily_units_before,
        pre.avg_daily_revenue_before,
        post.avg_daily_units_after,
        post.avg_daily_revenue_after,
        -- Volume impact
        case
            when coalesce(pre.avg_daily_units_before, 0) > 0
            then (coalesce(post.avg_daily_units_after, 0) - pre.avg_daily_units_before)
                 / pre.avg_daily_units_before * 100
            else null
        end as volume_change_pct,
        -- Revenue impact
        case
            when coalesce(pre.avg_daily_revenue_before, 0) > 0
            then (coalesce(post.avg_daily_revenue_after, 0) - pre.avg_daily_revenue_before)
                 / pre.avg_daily_revenue_before * 100
            else null
        end as revenue_change_pct,
        -- Net revenue impact (daily delta * 30 days projected)
        (coalesce(post.avg_daily_revenue_after, 0) - coalesce(pre.avg_daily_revenue_before, 0))
            * 30 as projected_monthly_revenue_impact,
        -- Impact classification
        case
            when coalesce(pre.avg_daily_revenue_before, 0) > 0
                and (coalesce(post.avg_daily_revenue_after, 0) - pre.avg_daily_revenue_before)
                     / pre.avg_daily_revenue_before * 100 > 10
            then 'revenue_positive'
            when coalesce(pre.avg_daily_revenue_before, 0) > 0
                and (coalesce(post.avg_daily_revenue_after, 0) - pre.avg_daily_revenue_before)
                     / pre.avg_daily_revenue_before * 100 < -10
            then 'revenue_negative'
            else 'revenue_neutral'
        end as impact_classification

    from pricing_changes as pc
    left join pre_change as pre
        on pc.pricing_history_id = pre.pricing_history_id
    left join post_change as post
        on pc.pricing_history_id = post.pricing_history_id

)

select * from final
