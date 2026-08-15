with

pricing_history as (

    select * from {{ ref('stg_pricing_history') }}

),

-- Generate month boundaries from pricing data
months as (

    select distinct
        {{ dbt.date_trunc('month', 'price_changed_date') }} as month_start

    from pricing_history

),

-- For each month, find the latest price change on or before month end
latest_price_per_month as (

    select
        m.month_start,
        ph.product_id,
        ph.new_price,
        ph.change_reason,
        ph.price_changed_date,
        row_number() over (
            partition by m.month_start, ph.product_id
            order by ph.price_changed_date desc
        ) as recency_rank

    from months as m

    inner join pricing_history as ph
        on ph.price_changed_date <= m.month_start + interval '1 month' - interval '1 day'

),

final as (

    select
        month_start,
        product_id,
        new_price as price_at_month_end,
        change_reason as last_change_reason,
        price_changed_date as last_price_change_date

    from latest_price_per_month
    where recency_rank = 1

)

select * from final
