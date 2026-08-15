with

monthly_gc as (
    select
        {{ sf_date_trunc('month', "issued_date") }} as activation_month,
        count(*) as cards_sold,
        sum(initial_balance) as total_value
    from {{ ref('dim_gift_cards') }}
    group by 1
),

compared as (
    select
        activation_month,
        cards_sold as current_cards,
        lag(cards_sold) over (order by activation_month) as prior_month_cards,
        total_value as current_value,
        lag(total_value) over (order by activation_month) as prior_month_value,
        round(((cards_sold - lag(cards_sold) over (order by activation_month))) * 100.0
            / nullif(lag(cards_sold) over (order by activation_month), 0), 2) as cards_mom_pct,
        round(((total_value - lag(total_value) over (order by activation_month))) * 100.0
            / nullif(lag(total_value) over (order by activation_month), 0), 2) as value_mom_pct
    from monthly_gc
)

select * from compared
