with

orders as (

    select * from {{ ref('orders') }}

),

loyalty_members as (

    select
        customer_id,
        enrolled_at as loyalty_signup_at
    from {{ ref('dim_loyalty_members') }}

),

customer_order_sequence as (

    select
        customer_id,
        order_id,
        ordered_at,
        customer_order_number
    from orders

),

first_order as (

    select
        customer_id,
        ordered_at as first_order_at
    from customer_order_sequence
    where customer_order_number = 1

),

second_order as (

    select
        customer_id,
        ordered_at as second_order_at
    from customer_order_sequence
    where customer_order_number = 2

),

third_order as (

    select
        customer_id,
        ordered_at as third_order_at
    from customer_order_sequence
    where customer_order_number = 3

),

onboarding_funnel as (

    select
        fo.customer_id,
        fo.first_order_at,
        so.second_order_at,
        to2.third_order_at,
        lm.loyalty_signup_at,
        case when so.second_order_at is not null then true else false end as reached_second_order,
        case
            when so.second_order_at is not null
            then {{ dbt.datediff('fo.first_order_at', 'so.second_order_at', 'day') }}
        end as days_to_second_order,
        case
            when so.second_order_at is not null
                and {{ dbt.datediff('fo.first_order_at', 'so.second_order_at', 'day') }} <= 30
            then true
            else false
        end as second_order_within_30d,
        case when to2.third_order_at is not null then true else false end as reached_third_order,
        case when lm.loyalty_signup_at is not null then true else false end as signed_up_loyalty
    from first_order as fo
    left join second_order as so on fo.customer_id = so.customer_id
    left join third_order as to2 on fo.customer_id = to2.customer_id
    left join loyalty_members as lm on fo.customer_id = lm.customer_id

),

summary as (

    select
        {{ dbt.date_trunc('month', 'first_order_at') }} as cohort_month,
        count(distinct customer_id) as stage_1_first_order,
        count(distinct case when second_order_within_30d then customer_id end) as stage_2_second_within_30d,
        count(distinct case when reached_second_order then customer_id end) as stage_2b_second_order_ever,
        count(distinct case when reached_third_order then customer_id end) as stage_3_third_order,
        count(distinct case when signed_up_loyalty then customer_id end) as stage_4_loyalty_signup,
        round(
            (count(distinct case when reached_second_order then customer_id end) * 100.0
            / nullif(count(distinct customer_id), 0)), 2
        ) as second_order_rate_pct,
        round(
            (count(distinct case when reached_third_order then customer_id end) * 100.0
            / nullif(count(distinct customer_id), 0)), 2
        ) as third_order_rate_pct,
        avg(days_to_second_order) as avg_days_to_second_order
    from onboarding_funnel
    group by 1

)

select * from summary
