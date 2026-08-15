{{
    config(
        materialized='incremental',
        unique_key='review_id'
    )
}}

with

reviews as (

    select * from {{ ref('stg_product_reviews') }}
    {% if is_incremental() %}
    where reviewed_date > (select max(reviewed_date) from {{ this }})
    {% endif %}

)

select
    review_id,
    product_id,
    customer_id,
    rating,
    reviewed_date,
    {{ dbt.date_trunc('month', 'reviewed_date') }} as review_month,
    case
        when rating >= 4 then 'positive'
        when rating >= 3 then 'neutral'
        else 'negative'
    end as sentiment

from reviews
