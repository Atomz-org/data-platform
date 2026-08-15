with

monthly_sales as (

    select
        product_id,
        sale_date,
        {{ dbt.date_trunc('month', 'sale_date') }} as sale_month,
        units_sold,
        daily_revenue
    from {{ ref('fct_product_sales') }}

),

products as (

    select product_id, product_name
    from {{ ref('stg_products') }}

),

monthly_agg as (

    select
        product_id,
        sale_month,
        sum(units_sold) as monthly_qty,
        sum(daily_revenue) as monthly_revenue,
        row_number() over (partition by product_id order by sale_month desc) as months_ago
    from monthly_sales
    group by 1, 2

),

trend as (

    select
        product_id,
        sum(case when months_ago <= 3 then monthly_qty else 0 end) as recent_3m_qty,
        sum(case when months_ago between 4 and 6 then monthly_qty else 0 end) as prior_3m_qty,
        sum(case when months_ago between 7 and 12 then monthly_qty else 0 end) as earlier_6m_qty,
        max(months_ago) as months_of_data
    from monthly_agg
    group by 1

),

final as (

    select
        t.product_id,
        p.product_name,
        t.recent_3m_qty,
        t.prior_3m_qty,
        t.earlier_6m_qty,
        t.months_of_data,
        case
            when t.prior_3m_qty > 0
            then (cast(t.recent_3m_qty as {{ dbt.type_float() }}) - t.prior_3m_qty) / t.prior_3m_qty * 100
            else null
        end as recent_vs_prior_growth_pct,
        case
            when t.recent_3m_qty = 0 then 'discontinued_candidate'
            when t.prior_3m_qty > 0
                and cast(t.recent_3m_qty as {{ dbt.type_float() }}) / t.prior_3m_qty < 0.5
            then 'declining_rapidly'
            when t.prior_3m_qty > 0
                and cast(t.recent_3m_qty as {{ dbt.type_float() }}) / t.prior_3m_qty < 0.8
            then 'declining'
            else 'stable_or_growing'
        end as lifecycle_status
    from trend as t
    inner join products as p on t.product_id = p.product_id

)

select * from final
