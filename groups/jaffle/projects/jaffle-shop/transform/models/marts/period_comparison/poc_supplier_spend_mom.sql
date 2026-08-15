with

monthly_supplier as (
    select
        order_month,
        supplier_id,
        total_spend,
        count_purchase_orders
    from {{ ref('int_supplier_spend_monthly') }}
),

compared as (
    select
        order_month,
        supplier_id,
        total_spend as current_spend,
        lag(total_spend) over (partition by supplier_id order by order_month) as prior_month_spend,
        count_purchase_orders as current_pos,
        lag(count_purchase_orders) over (partition by supplier_id order by order_month) as prior_month_pos,
        round(((total_spend - lag(total_spend) over (partition by supplier_id order by order_month))) * 100.0
            / nullif(lag(total_spend) over (partition by supplier_id order by order_month), 0), 2) as spend_mom_pct
    from monthly_supplier
)

select * from compared
