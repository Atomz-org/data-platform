select count(*) as total_products from {{ ref('stg_products') }}
