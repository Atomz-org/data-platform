select count(*) as supplier_count from {{ ref('dim_suppliers') }}
