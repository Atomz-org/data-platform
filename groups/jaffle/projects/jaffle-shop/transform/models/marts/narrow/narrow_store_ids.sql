select distinct location_id from {{ ref('stg_locations') }}
