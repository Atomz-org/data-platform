select count(*) as store_count from {{ ref('stg_locations') }}
