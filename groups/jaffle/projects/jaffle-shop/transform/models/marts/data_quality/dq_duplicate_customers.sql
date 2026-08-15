with

customers as (

    select * from {{ ref('stg_customers') }}

),

-- Find customer names that appear more than once
duplicate_names as (

    select
        customer_name,
        count(*) as name_occurrences
    from customers
    where customer_name is not null
    group by customer_name
    having count(*) > 1

),

-- Get all customers with duplicate names
duplicates as (

    select
        c.customer_id,
        c.customer_name,
        dn.name_occurrences,
        row_number() over (
            partition by c.customer_name
            order by c.customer_id
        ) as duplicate_rank

    from customers as c

    inner join duplicate_names as dn
        on c.customer_name = dn.customer_name

)

select * from duplicates
