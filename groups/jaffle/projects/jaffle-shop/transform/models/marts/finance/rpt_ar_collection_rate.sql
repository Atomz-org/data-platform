with

accounts_receivable as (

    select * from {{ ref('stg_accounts_receivable') }}

),

monthly_ar as (

    select
        {{ dbt.date_trunc('month', 'created_date') }} as report_month,
        count(receivable_id) as receivables_created,
        sum(amount_due) as total_amount_due,
        sum(amount_paid) as total_amount_collected,
        sum(amount_outstanding) as total_amount_outstanding,
        count(
            case when receivable_status = 'paid' then 1 end
        ) as fully_collected_count,
        count(
            case when receivable_status = 'partial' then 1 end
        ) as partially_collected_count,
        count(
            case when receivable_status = 'open' then 1 end
        ) as open_count

    from accounts_receivable
    group by 1

),

with_rates as (

    select
        report_month,
        receivables_created,
        total_amount_due,
        total_amount_collected,
        total_amount_outstanding,
        fully_collected_count,
        partially_collected_count,
        open_count,
        case
            when total_amount_due > 0
                then total_amount_collected / total_amount_due
            else 0
        end as collection_rate,
        case
            when receivables_created > 0
                then fully_collected_count::float / receivables_created
            else 0
        end as full_collection_rate,
        lag(
            case
                when total_amount_due > 0
                    then total_amount_collected / total_amount_due
                else 0
            end
        ) over (order by report_month) as prev_month_collection_rate,
        avg(
            case
                when total_amount_due > 0
                    then total_amount_collected / total_amount_due
                else 0
            end
        ) over (
            order by report_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_collection_rate

    from monthly_ar

)

select * from with_rates
