with

source as (

    select * from {{ source('finance', 'raw_budgets') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as budget_id,
        cast(store_id as varchar) as location_id,
        cast(category_id as varchar) as expense_category_id,

        ---------- text
        budget_type,

        ---------- numerics
        {{ cents_to_dollars('budgeted_amount') }} as budgeted_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'month_start') }} as budget_month

    from source

)

select * from renamed
