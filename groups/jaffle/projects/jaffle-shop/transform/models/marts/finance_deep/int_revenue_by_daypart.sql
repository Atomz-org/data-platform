with

orders as (

    select * from {{ ref('stg_orders') }}

),

invoices as (

    select * from {{ ref('stg_invoices') }}

),

order_with_invoice as (

    select
        o.order_id,
        o.location_id,
        o.ordered_at,
        i.total_amount,
        i.invoice_id
    from orders as o
    inner join invoices as i
        on o.order_id = i.order_id
    where i.invoice_status != 'draft'

),

daypart_classified as (

    select
        order_id,
        location_id,
        ordered_at,
        total_amount,
        case
            when extract(hour from ordered_at) >= 6 and extract(hour from ordered_at) < 11
                then 'morning'
            when extract(hour from ordered_at) >= 11 and extract(hour from ordered_at) < 14
                then 'lunch'
            when extract(hour from ordered_at) >= 14 and extract(hour from ordered_at) < 17
                then 'afternoon'
            else 'evening'
        end as daypart
    from order_with_invoice

),

final as (

    select
        ordered_at as revenue_date,
        location_id,
        daypart,
        count(distinct order_id) as order_count,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_order_value
    from daypart_classified
    group by 1, 2, 3

)

select * from final
