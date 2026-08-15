with

ar_aging as (

    select
        {{ dbt.date_trunc('month', 'created_date') }} as report_month,
        avg(days_past_due) as avg_days_receivable
    from {{ ref('int_accounts_receivable_aging') }}
    group by 1

),

inventory as (

    select
        current_date as report_month,
        sum(current_quantity) as total_units,
        avg(current_quantity) as avg_units_per_product
    from {{ ref('int_inventory_current_level') }}

),

daily_usage as (

    select
        avg(daily_depletion_rate) as avg_daily_depletion
    from {{ ref('int_stock_depletion_rate') }}
    where daily_depletion_rate > 0

),

po_payment as (

    select
        {{ dbt.date_trunc('month', 'ordered_at') }} as report_month,
        avg({{ dbt.datediff('ordered_at', 'expected_delivery_at', 'day') }}) as avg_days_payable
    from {{ ref('fct_purchase_orders') }}
    group by 1

),

final as (

    select
        ar.report_month,
        ar.avg_days_receivable,
        case
            when du.avg_daily_depletion > 0
            then inv.total_units / du.avg_daily_depletion
            else null
        end as days_inventory_on_hand,
        pp.avg_days_payable,
        ar.avg_days_receivable
            + coalesce(
                case when du.avg_daily_depletion > 0
                     then inv.total_units / du.avg_daily_depletion
                     else 0 end, 0)
            - coalesce(pp.avg_days_payable, 0)
        as cash_conversion_cycle_days
    from ar_aging as ar
    cross join inventory as inv
    cross join daily_usage as du
    left join po_payment as pp
        on ar.report_month = pp.report_month

)

select * from final
