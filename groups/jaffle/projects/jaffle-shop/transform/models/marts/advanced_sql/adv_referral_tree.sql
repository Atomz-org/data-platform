-- adv_referral_tree.sql
-- Technique: Recursive CTE

{% set referral_chain_q %}select * from {{ ref('int_referral_chain') }}{% endset %}
{% set orders_q %}select * from {{ ref('stg_orders') }}{% endset %}

with recursive

customer_revenue as (
    select
        customer_id,
        coalesce(sum(order_total), 0) as lifetime_revenue
    from ({{ orders_q }}) as _orders
    group by 1
),

roots as (
    select distinct referrer_customer_id as customer_id
    from ({{ referral_chain_q }}) as _rc1
    where referral_status = 'converted'
      and referrer_customer_id not in (
          select referee_customer_id
          from ({{ referral_chain_q }}) as _rc2
          where referral_status = 'converted'
      )
),

referral_tree as (
    -- Anchor: root referrers
    select
        r.customer_id as root_referrer_id,
        r.customer_id as current_member_id,
        0 as depth,
        r.customer_id::text as chain_path,
        coalesce(cr.lifetime_revenue, 0) as total_chain_revenue
    from roots as r
    left join customer_revenue as cr on r.customer_id = cr.customer_id

    union all

    select
        parent.root_referrer_id,
        rc.referee_customer_id as current_member_id,
        parent.depth + 1 as depth,
        parent.chain_path || ' > ' || rc.referee_customer_id::text as chain_path,
        parent.total_chain_revenue + coalesce(cr.lifetime_revenue, 0) as total_chain_revenue
    from referral_tree as parent
    inner join ({{ referral_chain_q }}) as rc
        on parent.current_member_id = rc.referrer_customer_id
        and rc.referral_status = 'converted'
    left join customer_revenue as cr on rc.referee_customer_id = cr.customer_id
    where parent.depth < 20
)

select
    root_referrer_id,
    current_member_id,
    depth,
    chain_path,
    total_chain_revenue
from referral_tree
order by root_referrer_id, depth, current_member_id
