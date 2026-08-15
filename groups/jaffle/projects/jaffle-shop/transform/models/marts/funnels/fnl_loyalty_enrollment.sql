with

customers as (

    select
        customer_id,
        customer_name
    from {{ ref('stg_customers') }}

),

loyalty_members as (

    select
        customer_id,
        loyalty_member_id,
        enrolled_at
    from {{ ref('stg_loyalty_members') }}

),

loyalty_txns as (

    select
        loyalty_member_id,
        transaction_type,
        transacted_at,
        points
    from {{ ref('fct_loyalty_transactions') }}

),

-- Stage 1: All customers
stage_customer as (

    select count(distinct customer_id) as total_customers
    from customers

),

-- Stage 2: Signed up for loyalty
stage_loyalty_signup as (

    select count(distinct customer_id) as loyalty_signups
    from loyalty_members

),

-- Stage 3: First points earn
first_earn as (

    select
        loyalty_member_id,
        min(transacted_at) as first_earn_at
    from loyalty_txns
    where transaction_type = 'earn'
    group by 1

),

stage_first_earn as (

    select count(distinct loyalty_member_id) as first_earners
    from first_earn

),

-- Stage 4: First redemption
first_redemption as (

    select
        loyalty_member_id,
        min(transacted_at) as first_redemption_at
    from loyalty_txns
    where transaction_type = 'redeem'
    group by 1

),

stage_first_redemption as (

    select count(distinct loyalty_member_id) as first_redeemers
    from first_redemption

),

funnel as (

    select
        sc.total_customers as stage_1_total_customers,
        ls.loyalty_signups as stage_2_loyalty_signups,
        fe.first_earners as stage_3_first_earn,
        fr.first_redeemers as stage_4_first_redemption,
        round(ls.loyalty_signups * 100.0 / nullif(sc.total_customers, 0), 2) as signup_rate_pct,
        round(fe.first_earners * 100.0 / nullif(ls.loyalty_signups, 0), 2) as earn_rate_pct,
        round(fr.first_redeemers * 100.0 / nullif(fe.first_earners, 0), 2) as redemption_rate_pct,
        round(fr.first_redeemers * 100.0 / nullif(sc.total_customers, 0), 2) as overall_conversion_pct
    from stage_customer as sc
    cross join stage_loyalty_signup as ls
    cross join stage_first_earn as fe
    cross join stage_first_redemption as fr

)

select * from funnel
