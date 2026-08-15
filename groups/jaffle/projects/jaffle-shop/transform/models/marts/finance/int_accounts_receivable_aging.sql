with

accounts_receivable as (

    select * from {{ ref('stg_accounts_receivable') }}

),

aged as (

    select
        receivable_id,
        customer_id,
        invoice_id,
        receivable_status,
        amount_due,
        amount_paid,
        amount_outstanding,
        due_date,
        created_date,
        {{ sf_datediff('day', "due_date", "current_date") }} as days_past_due,
        case
            when {{ sf_datediff('day', "due_date", "current_date") }} <= 0 then 'current'
            when {{ sf_datediff('day', "due_date", "current_date") }} between 1 and 30 then '1-30 days'
            when {{ sf_datediff('day', "due_date", "current_date") }} between 31 and 60 then '31-60 days'
            when {{ sf_datediff('day', "due_date", "current_date") }} between 61 and 90 then '61-90 days'
            when {{ sf_datediff('day', "due_date", "current_date") }} > 90 then '90+ days'
        end as aging_bucket,
        case
            when {{ sf_datediff('day', "due_date", "current_date") }} <= 0 then 1
            when {{ sf_datediff('day', "due_date", "current_date") }} between 1 and 30 then 2
            when {{ sf_datediff('day', "due_date", "current_date") }} between 31 and 60 then 3
            when {{ sf_datediff('day', "due_date", "current_date") }} between 61 and 90 then 4
            when {{ sf_datediff('day', "due_date", "current_date") }} > 90 then 5
        end as aging_bucket_sort

    from accounts_receivable
    where receivable_status in ('open', 'partial')

)

select * from aged
