with

pricing as (

    select * from {{ ref('stg_pricing_history') }}

),

latest_price_change as (

    select
        product_id,
        max(price_changed_date) as last_price_change_date,
        count(*) as total_price_changes

    from pricing
    group by product_id

),

products as (

    select
        product_id,
        product_name,
        product_price
    from {{ ref('stg_products') }}

),

stale as (

    select
        p.product_id,
        p.product_name,
        p.product_price as current_price,
        lpc.last_price_change_date,
        lpc.total_price_changes,
        {{ dbt.datediff('lpc.last_price_change_date', dbt.current_timestamp(), 'day') }} as days_since_last_change,
        case
            when lpc.last_price_change_date is null then 'never_updated'
            when {{ dbt.datediff('lpc.last_price_change_date', dbt.current_timestamp(), 'day') }} >= 365
            then 'critically_stale'
            when {{ dbt.datediff('lpc.last_price_change_date', dbt.current_timestamp(), 'day') }} >= 180
            then 'stale'
            else 'recent'
        end as staleness_level

    from products as p

    left join latest_price_change as lpc
        on p.product_id = lpc.product_id

    where lpc.last_price_change_date is null
       or {{ dbt.datediff('lpc.last_price_change_date', dbt.current_timestamp(), 'day') }} >= 180

)

select * from stale
