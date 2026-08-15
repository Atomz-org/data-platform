with

contracts as (

    select * from {{ ref('stg_supplier_contracts') }}

),

suppliers as (

    select
        supplier_id,
        supplier_name
    from {{ ref('stg_suppliers') }}

),

final as (

    select
        c.contract_id,
        c.supplier_id,
        s.supplier_name,
        c.contract_type,
        c.payment_terms,
        c.minimum_order_amount,
        c.lead_time_days,
        c.effective_date,
        c.expiration_date,
        {{ dbt.datediff(dbt.current_timestamp(), 'c.expiration_date', 'day') }} as days_until_expiry,
        case
            when c.expiration_date < {{ dbt.current_timestamp() }} then 'expired'
            when {{ dbt.datediff(dbt.current_timestamp(), 'c.expiration_date', 'day') }} <= 30 then 'critical'
            when {{ dbt.datediff(dbt.current_timestamp(), 'c.expiration_date', 'day') }} <= 60 then 'warning'
            when {{ dbt.datediff(dbt.current_timestamp(), 'c.expiration_date', 'day') }} <= 90 then 'upcoming'
            else 'active'
        end as expiry_urgency
    from contracts as c
    left join suppliers as s
        on c.supplier_id = s.supplier_id

)

select * from final
