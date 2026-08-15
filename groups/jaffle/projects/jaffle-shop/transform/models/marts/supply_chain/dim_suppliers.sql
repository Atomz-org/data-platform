with

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

contracts as (

    select * from {{ ref('stg_supplier_contracts') }}

),

active_contracts as (

    select
        supplier_id,
        count(contract_id) as total_contracts,
        sum(
            case
                when expiration_date >= {{ dbt.current_timestamp() }}
                    and effective_date <= {{ dbt.current_timestamp() }}
                    then 1
                else 0
            end
        ) as active_contracts,
        min(lead_time_days) as min_contracted_lead_time_days,
        max(lead_time_days) as max_contracted_lead_time_days,
        min(effective_date) as earliest_contract_date,
        max(expiration_date) as latest_contract_expiration

    from contracts

    group by supplier_id

),

final as (

    select
        suppliers.supplier_id,
        suppliers.supplier_name,
        suppliers.contact_name,
        suppliers.contact_email,
        suppliers.phone,
        suppliers.address,
        suppliers.city,
        suppliers.state,
        suppliers.country,
        suppliers.is_active,
        suppliers.created_at,
        coalesce(active_contracts.total_contracts, 0) as total_contracts,
        coalesce(active_contracts.active_contracts, 0) as active_contracts,
        active_contracts.min_contracted_lead_time_days,
        active_contracts.max_contracted_lead_time_days,
        active_contracts.earliest_contract_date,
        active_contracts.latest_contract_expiration

    from suppliers

    left join active_contracts
        on suppliers.supplier_id = active_contracts.supplier_id

)

select * from final
