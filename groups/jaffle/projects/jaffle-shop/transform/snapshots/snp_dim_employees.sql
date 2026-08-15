{% snapshot snp_dim_employees %}

{{
    config(
        target_schema='snapshots',
        unique_key='employee_id',
        strategy='check',
        check_cols=['department_name', 'position_title', 'is_active']
    )
}}

select * from {{ ref('dim_employees') }}

{% endsnapshot %}
