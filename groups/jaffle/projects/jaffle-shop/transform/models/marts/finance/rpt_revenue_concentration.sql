with

invoices as (

    select * from {{ ref('fct_invoices') }}
    where is_paid = true

),

customers as (

    select * from {{ ref('stg_customers') }}

),

customer_revenue as (

    select
        inv.customer_id,
        c.customer_name,
        count(inv.invoice_id) as invoice_count,
        sum(inv.total_amount) as total_revenue,
        avg(inv.total_amount) as avg_invoice_amount,
        min(inv.issued_date) as first_invoice_date,
        max(inv.issued_date) as last_invoice_date

    from invoices as inv
    left join customers as c
        on inv.customer_id = c.customer_id
    group by 1, 2

),

ranked as (

    select
        customer_id,
        customer_name,
        invoice_count,
        total_revenue,
        avg_invoice_amount,
        first_invoice_date,
        last_invoice_date,
        sum(total_revenue) over () as grand_total_revenue,
        count(*) over () as total_customer_count,
        total_revenue / nullif(sum(total_revenue) over (), 0) as revenue_share_pct,
        row_number() over (order by total_revenue desc) as revenue_rank,
        ntile(10) over (order by total_revenue desc) as revenue_decile,
        sum(total_revenue) over (
            order by total_revenue desc
            rows between unbounded preceding and current row
        ) as cumulative_revenue,
        sum(total_revenue) over (
            order by total_revenue desc
            rows between unbounded preceding and current row
        ) / nullif(sum(total_revenue) over (), 0) as cumulative_revenue_pct

    from customer_revenue

),

final as (

    select
        customer_id,
        customer_name,
        invoice_count,
        total_revenue,
        avg_invoice_amount,
        first_invoice_date,
        last_invoice_date,
        grand_total_revenue,
        total_customer_count,
        revenue_share_pct,
        revenue_rank,
        revenue_decile,
        cumulative_revenue,
        cumulative_revenue_pct,
        case
            when revenue_decile = 1 then 'top_10_pct'
            when revenue_decile <= 2 then 'top_20_pct'
            when revenue_decile <= 5 then 'top_50_pct'
            else 'bottom_50_pct'
        end as concentration_tier

    from ranked

)

select * from final
