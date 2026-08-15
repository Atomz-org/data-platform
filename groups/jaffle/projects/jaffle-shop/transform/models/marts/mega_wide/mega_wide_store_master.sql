{{
    config(
        materialized='table',
        tags=['mega_wide', 'store_master']
    )
}}

/*
    mega_wide_store_master
    ----------------------
    One row per store / location. The ultimate denormalized store dimension
    combining revenue, customers, products, labor, inventory, financial,
    operations, and scoring metrics (80+ columns).
*/

-- ============================================================
-- Store identity
-- ============================================================
with

l as (
    select * from {{ ref('stg_locations') }}
),

sp as (
    select * from {{ ref('dim_store_profile') }}
),

o as (
    select * from {{ ref('stg_orders') }}
),

lm as (
    select * from {{ ref('dim_loyalty_members') }}
),

ps as (
    select * from {{ ref('int_product_sales_by_location') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

lcd as (
    select * from {{ ref('int_labor_cost_daily') }}
),

e as (
    select * from {{ ref('dim_employees') }}
),

icl as (
    select * from {{ ref('int_inventory_current_level') }}
),

we as (
    select * from {{ ref('fct_waste_events') }}
),

fe as (
    select * from {{ ref('fct_expenses') }}
),

eq as (
    select * from {{ ref('dim_equipment') }}
),

sh as (
    select * from {{ ref('scr_store_health') }}
),

mmr as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),


store_base as (

    select
        l.location_id,
        l.location_name,
        l.tax_rate,
        l.opened_date,
        {{ dbt.datediff('l.opened_date', 'current_date', 'month') }} / 12 * 12
            + {{ dbt.datediff('l.opened_date', 'current_date', 'month') }}          as store_age_months
    from l

),

store_identity as (

    select
        sb.*,
        case
            when sb.store_age_months < 6   then '0-6 months'
            when sb.store_age_months < 12  then '6-12 months'
            when sb.store_age_months < 24  then '1-2 years'
            when sb.store_age_months < 60  then '2-5 years'
            else '5+ years'
        end                                                                 as store_age_bucket
    from store_base sb

),

-- ============================================================
-- Store profile (if available)
-- ============================================================
store_profile as (

    select
        sp.location_id
    from sp

),

-- ============================================================
-- Revenue lifetime
-- ============================================================
order_base as (

    select
        o.location_id,
        o.order_id,
        o.customer_id,
        o.ordered_at::date                                                  as order_date,
        o.order_total,
        {{ sf_date_trunc('month', "o.ordered_at") }}::date                             as order_month
    from o
    where o.ordered_at is not null

),

revenue_lifetime as (

    select
        ob.location_id,
        coalesce(sum(ob.order_total), 0)                                    as total_lifetime_revenue,
        count(distinct ob.order_id)                                         as total_lifetime_orders,
        avg(ob.order_total)                                                 as avg_order_value,
        sum(case when ob.order_date >= current_date - 30 then ob.order_total else 0 end)   as revenue_last_30d,
        sum(case when ob.order_date >= current_date - 90 then ob.order_total else 0 end)   as revenue_last_90d,
        sum(case when ob.order_date >= current_date - 365 then ob.order_total else 0 end)  as revenue_last_365d,
        max(ob.order_total)                                                 as peak_daily_revenue,
        avg(ob.order_total)                                                 as avg_daily_revenue
    from order_base ob
    group by 1

),

-- ============================================================
-- Monthly revenue for growth & volatility
-- ============================================================
monthly_revenue as (

    select
        ob.location_id,
        ob.order_month,
        sum(ob.order_total)                                                 as monthly_revenue,
        count(distinct ob.order_id)                                         as monthly_orders,
        count(distinct ob.customer_id)                                      as monthly_customers
    from order_base ob
    group by 1, 2

),

monthly_revenue_stats as (

    select
        mr.location_id,
        avg(mr.monthly_revenue)                                             as avg_monthly_revenue,
        max(mr.monthly_revenue)                                             as best_month_revenue,
        min(mr.monthly_revenue)                                             as worst_month_revenue,
        stddev(mr.monthly_revenue)                                          as revenue_volatility,
        avg(mr.monthly_customers)                                           as monthly_avg_customers
    from monthly_revenue mr
    group by 1

),

monthly_growth as (

    select
        location_id,
        revenue_growth_mom
    from (
        select
            mr.location_id,
            case when lag(mr.monthly_revenue) over (
                    partition by mr.location_id order by mr.order_month
                 ) > 0
                 then round(((mr.monthly_revenue - lag(mr.monthly_revenue) over (
                    partition by mr.location_id order by mr.order_month
                 )) / lag(mr.monthly_revenue) over (
                    partition by mr.location_id order by mr.order_month
                 ) * 100), 2)
                 else 0
            end                                                                 as revenue_growth_mom,
            row_number() over (partition by mr.location_id order by mr.order_month desc) as _rn
        from monthly_revenue mr
    ) ranked
    where _rn = 1

),

yoy_growth as (

    select
        mr_curr.location_id,
        case when coalesce(sum(mr_prev.monthly_revenue), 0) > 0
             then round(((sum(mr_curr.monthly_revenue) - sum(mr_prev.monthly_revenue))
                        / sum(mr_prev.monthly_revenue) * 100), 2)
             else 0
        end                                                                 as revenue_growth_yoy
    from monthly_revenue mr_curr
    left join monthly_revenue mr_prev
        on mr_curr.location_id = mr_prev.location_id
        and mr_curr.order_month = mr_prev.order_month + interval '1 year'
    where mr_curr.order_month >= {{ sf_date_trunc('month', "(current_date - interval '12 months')") }}
    group by 1

),

-- ============================================================
-- Customers
-- ============================================================
customer_metrics as (

    select
        ob.location_id,
        count(distinct ob.customer_id)                                      as total_unique_customers,
        count(distinct case when ob.order_date >= current_date - 30
                            then ob.customer_id end)                        as customers_active_last_30d
    from order_base ob
    group by 1

),

new_customers_30d as (

    select
        ob.location_id,
        count(distinct ob.customer_id)                                      as new_customers_last_30d
    from order_base ob
    inner join (
        select customer_id, min(order_date) as first_date
        from order_base
        group by 1
    ) first_ord on ob.customer_id = first_ord.customer_id
                and first_ord.first_date >= current_date - 30
    where ob.order_date >= current_date - 30
    group by 1

),

customer_spend_stats as (

    select
        ob.location_id,
        avg(customer_total)                                                 as avg_customer_spend,
        max(customer_total)                                                 as top_customer_spend
    from (
        select location_id, customer_id, sum(order_total) as customer_total
        from order_base
        group by 1, 2
    ) ob
    group by 1

),

returning_rate as (

    select
        ob.location_id,
        round(count(distinct case when order_count > 1 then ob.customer_id end)::numeric
              / nullif(count(distinct ob.customer_id), 0) * 100, 2)         as returning_customer_pct,
        avg(order_count)                                                    as avg_visits_per_customer
    from (
        select location_id, customer_id, count(*) as order_count
        from order_base
        group by 1, 2
    ) ob
    group by 1

),

loyalty_member_rate as (

    select
        ob.location_id,
        round(count(distinct case when lm.customer_id is not null then ob.customer_id end)::numeric
              / nullif(count(distinct ob.customer_id), 0) * 100, 2)         as loyalty_member_pct
    from order_base ob
    left join lm on ob.customer_id = lm.customer_id
    group by 1

),

customer_concentration as (

    -- Herfindahl index proxy: sum of squared revenue shares
    select
        sub.location_id,
        round(sum(sub.share * sub.share) * 10000, 2)                       as customer_concentration_index
    from (
        select
            ob.location_id,
            ob.customer_id,
            sum(ob.order_total)::numeric / nullif(sum(sum(ob.order_total)) over (partition by ob.location_id), 0) as share
        from order_base ob
        group by 1, 2
    ) sub
    group by 1

),

-- ============================================================
-- Products
-- ============================================================
product_sales as (

    select
        ps.location_id,
        count(distinct ps.product_id)                                       as unique_products_sold,
        sum(case when ps.product_type = 'food' then ps.daily_revenue else 0 end)
            / nullif(sum(ps.daily_revenue), 0) * 100                        as food_revenue_pct,
        sum(case when ps.product_type = 'beverage' then ps.daily_revenue else 0 end)
            / nullif(sum(ps.daily_revenue), 0) * 100                        as beverage_revenue_pct,
        avg(0)                                                      as avg_product_margin,
        count(distinct ps.product_type)                                     as product_mix_diversity,
        sum(case when false then ps.units_sold else 0 end)      as seasonal_items_sold
    from ps
    group by 1

),

top_product_per_store as (

    select
        location_id,
        top_product_id,
        top_product_name,
        top_product_revenue
    from (
        select
            ps.location_id,
            ps.product_id                                                       as top_product_id,
            ps.product_name                                                     as top_product_name,
            ps.daily_revenue                                                    as top_product_revenue,
            row_number() over (partition by ps.location_id order by ps.daily_revenue desc) as _rn
        from ps
    ) ranked
    where _rn = 1

),

avg_items_per_order as (

    select
        o.location_id,
        avg(item_count)                                                     as avg_items_per_order
    from (
        select oi.order_id, count(*) as item_count
        from oi
        group by 1
    ) ic
    inner join o on ic.order_id = o.order_id
    group by 1

),

-- ============================================================
-- Labor
-- ============================================================
labor as (

    select
        lcd.location_id,
        avg(lcd.total_labor_cost)                                           as avg_monthly_labor_cost,
        avg(lcd.employee_count)                                             as avg_employee_count,
        0 as overtime_pct
    from lcd
    group by 1

),

labor_cost_pct as (

    select
        lcd.location_id,
        case when coalesce(rl.total_lifetime_revenue, 0) > 0
             then round(sum(lcd.total_labor_cost)::numeric / rl.total_lifetime_revenue * 100, 2)
             else 0
        end                                                                 as labor_cost_pct_revenue,
        case when sum(lcd.total_hours) > 0
             then round(rl.total_lifetime_orders::numeric / sum(lcd.total_hours), 2)
             else 0
        end                                                                 as avg_orders_per_labor_hour
    from lcd
    inner join revenue_lifetime rl on lcd.location_id = rl.location_id
    group by lcd.location_id, rl.total_lifetime_revenue, rl.total_lifetime_orders

),

employees as (

    select
        e.location_id,
        count(*)                                                            as current_headcount,
        avg({{ dbt.datediff('e.hire_date', 'current_date', 'month') }} / 12 * 12
            + {{ dbt.datediff('e.hire_date', 'current_date', 'month') }})           as avg_employee_tenure_months,
        0                                            as avg_performance_score,
        round(count(case when e.termination_date is not null then 1 end)::numeric
              / nullif(count(*), 0) * 100, 2)                              as employee_turnover_rate,
        0 as training_completion_pct
    from e
    group by 1

),

-- ============================================================
-- Inventory & Waste
-- ============================================================
inventory_current as (

    select
        icl.location_id,
        sum(icl.current_quantity)                                              as current_inventory_value,
        sum(0)                                  as monthly_procurement_spend,
        avg(0)                                             as avg_lead_time_days,
        sum(0)                                             as stockout_frequency_monthly,
        avg(0)                                              as inventory_turnover_monthly
    from icl
    group by 1

),

waste as (

    select
        we.location_id,
        avg(monthly_waste_cost)                                             as avg_monthly_waste_cost
    from (
        select
            location_id,
            {{ sf_date_trunc('month', "wasted_at") }} as waste_month,
            sum(cost_of_waste) as monthly_waste_cost
        from {{ ref('fct_waste_events') }}
        group by 1, 2
    ) we
    group by 1

),

top_wasted as (

    select
        location_id,
        product_id as top_wasted_product
    from (
        select
            we.location_id,
            we.product_id,
            row_number() over (partition by we.location_id order by sum(we.cost_of_waste) desc) as _rn
        from we
        group by we.location_id, we.product_id
    ) ranked
    where _rn = 1

),

-- ============================================================
-- Financial (from P&L report)
-- ============================================================
pnl as (

    select
        location_id,
        total_costs,
        net_profit_margin_pct,
        net_profit,
        monthly_revenue,
        opex_ratio_pct,
        marketing_ratio_pct,
        labor_cost_ratio_pct
    from {{ ref('rpt_store_pnl') }}

),

cost_per_order as (

    select
        ob.location_id,
        case when count(distinct ob.order_id) > 0
             then round(sum(fe.expense_amount)::numeric / count(distinct ob.order_id), 2)
             else 0
        end                                                                 as cost_per_order
    from order_base ob
    left join fe
        on ob.location_id = fe.location_id
    group by 1

),

waste_pct as (

    select
        w.location_id,
        case when coalesce(rl.total_lifetime_revenue, 0) > 0
             then round(w.avg_monthly_waste_cost::numeric * 12 / rl.total_lifetime_revenue * 100, 2)
             else 0
        end                                                                 as waste_pct_revenue
    from waste w
    inner join revenue_lifetime rl on w.location_id = rl.location_id

),

-- ============================================================
-- Equipment & Maintenance
-- ============================================================
equipment as (

    select
        eq.location_id,
        count(*)                                                            as equipment_count
    from eq
    group by 1

),

maintenance as (

    select
        me.location_id,
        avg(monthly_cost)                                                   as monthly_maintenance_cost
    from (
        select
            location_id,
            {{ sf_date_trunc('month', "scheduled_date") }} as maint_month,
            sum(maintenance_cost) as monthly_cost
        from {{ ref('fct_maintenance_events') }}
        group by 1, 2
    ) me
    group by 1

),

peak_hour as (

    select
        location_id,
        peak_hour
    from (
        select
            o.location_id,
            extract(hour from o.ordered_at)::int                                as peak_hour,
            row_number() over (partition by o.location_id order by count(*) desc) as _rn
        from o
        where o.ordered_at is not null
        group by o.location_id, extract(hour from o.ordered_at)
    ) ranked
    where _rn = 1

),

-- ============================================================
-- Store health scores
-- ============================================================
health as (

    select
        sh.location_id,
        sh.store_health_score,
        sh.health_tier
    from sh

),

-- ============================================================
-- Met monthly revenue (for ranking)
-- ============================================================
met_revenue as (

    select
        mmr.location_id,
        sum(mmr.monthly_revenue)                                                    as met_total_revenue,
        sum(0)                                                     as met_total_profit
    from mmr
    group by 1

),

-- ============================================================
-- Rankings
-- ============================================================
rankings as (

    select
        mr.location_id,
        rank() over (order by mr.met_total_revenue desc)                    as revenue_rank,
        rank() over (order by mr.met_total_profit desc)                     as profit_rank,
        rank() over (order by coalesce(lcp.avg_orders_per_labor_hour, 0) desc) as efficiency_rank
    from met_revenue mr
    left join labor_cost_pct lcp on mr.location_id = lcp.location_id

),

-- Service speed proxy
service_speed as (

    select
        ob.location_id,
        avg(ob.order_total)                                                 as avg_service_speed_proxy
        -- In reality this would use timestamps; proxy uses order value as placeholder
    from order_base ob
    group by 1

),

-- ============================================================
-- Final assembly
-- ============================================================
final as (

    select
        -- ── Identity (6) ────────────────────────────────────────
        si.location_id,
        si.location_name,
        si.tax_rate,
        si.opened_date,
        si.store_age_months,
        si.store_age_bucket,

        -- ── Revenue (14) ────────────────────────────────────────
        coalesce(rl.total_lifetime_revenue, 0)                              as total_lifetime_revenue,
        coalesce(rl.total_lifetime_orders, 0)                               as total_lifetime_orders,
        coalesce(mrs.avg_monthly_revenue, 0)                                as avg_monthly_revenue,
        rl.avg_order_value,
        coalesce(rl.revenue_last_30d, 0)                                    as revenue_last_30d,
        coalesce(rl.revenue_last_90d, 0)                                    as revenue_last_90d,
        coalesce(rl.revenue_last_365d, 0)                                   as revenue_last_365d,
        coalesce(mg.revenue_growth_mom, 0)                                  as revenue_growth_mom,
        coalesce(yg.revenue_growth_yoy, 0)                                  as revenue_growth_yoy,
        coalesce(mrs.best_month_revenue, 0)                                 as best_month_revenue,
        coalesce(mrs.worst_month_revenue, 0)                                as worst_month_revenue,
        coalesce(mrs.revenue_volatility, 0)                                 as revenue_volatility,
        coalesce(rl.peak_daily_revenue, 0)                                  as peak_daily_revenue,
        coalesce(rl.avg_daily_revenue, 0)                                   as avg_daily_revenue,

        -- ── Customers (10) ──────────────────────────────────────
        coalesce(cm.total_unique_customers, 0)                              as total_unique_customers,
        coalesce(mrs.monthly_avg_customers, 0)                              as monthly_avg_customers,
        coalesce(nc.new_customers_last_30d, 0)                              as new_customers_last_30d,
        coalesce(rr.returning_customer_pct, 0)                              as returning_customer_pct,
        css.avg_customer_spend,
        coalesce(css.top_customer_spend, 0)                                 as top_customer_spend,
        round(coalesce(cm.customers_active_last_30d, 0)::numeric
              / nullif(cm.total_unique_customers, 0) * 100, 2)              as customer_retention_rate,
        coalesce(lmr.loyalty_member_pct, 0)                                 as loyalty_member_pct,
        coalesce(rr.avg_visits_per_customer, 0)                             as avg_visits_per_customer,
        coalesce(cc.customer_concentration_index, 0)                        as customer_concentration_index,

        -- ── Products (10) ───────────────────────────────────────
        coalesce(prs.unique_products_sold, 0)                               as unique_products_sold,
        aipo.avg_items_per_order,
        tps.top_product_id,
        tps.top_product_name,
        coalesce(tps.top_product_revenue, 0)                                as top_product_revenue,
        coalesce(prs.food_revenue_pct, 0)                                   as food_revenue_pct,
        coalesce(prs.beverage_revenue_pct, 0)                               as beverage_revenue_pct,
        prs.avg_product_margin,
        coalesce(prs.product_mix_diversity, 0)                              as product_mix_diversity,
        coalesce(prs.seasonal_items_sold, 0)                                as seasonal_items_sold,

        -- ── Labor (12) ──────────────────────────────────────────
        coalesce(emp.current_headcount, 0)                                  as current_headcount,
        coalesce(lab.avg_monthly_labor_cost, 0)                             as avg_monthly_labor_cost,
        coalesce(lcp.labor_cost_pct_revenue, 0)                             as labor_cost_pct_revenue,
        coalesce(lcp.avg_orders_per_labor_hour, 0)                          as avg_orders_per_labor_hour,
        coalesce(0, 0)                       as total_overtime_hours_monthly,
        coalesce(lab.overtime_pct, 0)                                       as overtime_pct,
        coalesce(0, 0)                                 as avg_shift_coverage,
        coalesce(emp.training_completion_pct, 0)                             as employee_turnover_rate,
        coalesce(emp.avg_employee_tenure_months, 0)                         as avg_employee_tenure_months,
        coalesce(emp.training_completion_pct, 0)                           as training_completion_rate,
        0,
        coalesce(0, 0)                                   as absenteeism_rate,

        -- ── Inventory & Supply (8) ──────────────────────────────
        coalesce(inv.current_inventory_value, 0)                            as current_inventory_value,
        coalesce(w.avg_monthly_waste_cost, 0)                               as avg_monthly_waste_cost,
        coalesce(wp.waste_pct_revenue, 0)                                   as waste_pct_revenue,
        coalesce(inv.monthly_procurement_spend, 0)                          as monthly_procurement_spend,
        coalesce(inv.avg_lead_time_days, 0)                                 as avg_lead_time_days,
        coalesce(inv.stockout_frequency_monthly, 0)                         as stockout_frequency_monthly,
        coalesce(inv.inventory_turnover_monthly, 0)                         as inventory_turnover_monthly,
        tw.top_wasted_product,

        -- ── Financial (10) ──────────────────────────────────────
        coalesce(pnl.total_costs, 0)                             as total_expenses_monthly,
        coalesce(pnl.net_profit_margin_pct, 0)                                as expense_pct_revenue,
        coalesce(pnl.net_profit, 0)                                       as gross_margin,
        coalesce(pnl.net_profit_margin_pct, 0)                                         as net_margin,
        coalesce(pnl.net_profit, 0)                                     as monthly_profit,
        coalesce(pnl.monthly_revenue, 0)                         as break_even_monthly_revenue,
        coalesce(pnl.opex_ratio_pct, 0)                                as budget_variance_pct,
        coalesce(pnl.marketing_ratio_pct, 0)                                     as ar_outstanding,
        coalesce(pnl.labor_cost_ratio_pct, 0)                                as gift_card_liability,
        coalesce(cpo.cost_per_order, 0)                                     as cost_per_order,

        -- ── Operations (6) ──────────────────────────────────────
        coalesce(eqp.equipment_count, 0)                                    as equipment_count,
        coalesce(0, 0)                                  as equipment_avg_age,
        coalesce(mnt.monthly_maintenance_cost, 0)                           as monthly_maintenance_cost,
        coalesce(0, 0)                               as equipment_uptime_pct,
        ss.avg_service_speed_proxy,
        ph.peak_hour,

        -- ── Scoring (6) ────────────────────────────────────────
        h.store_health_score,
        h.health_tier,
        coalesce(rnk.revenue_rank, 0)                                       as revenue_rank,
        coalesce(rnk.profit_rank, 0)                                        as profit_rank,
        coalesce(rnk.efficiency_rank, 0)                                    as efficiency_rank,
        round((coalesce(rnk.revenue_rank, 0)
             + coalesce(rnk.profit_rank, 0)
             + coalesce(rnk.efficiency_rank, 0)) / 3.0, 1)                 as overall_rank

    from store_identity si
    left join store_profile sprof             on si.location_id = sprof.location_id
    left join revenue_lifetime rl             on si.location_id = rl.location_id
    left join monthly_revenue_stats mrs       on si.location_id = mrs.location_id
    left join monthly_growth mg               on si.location_id = mg.location_id
    left join yoy_growth yg                   on si.location_id = yg.location_id
    left join customer_metrics cm             on si.location_id = cm.location_id
    left join new_customers_30d nc            on si.location_id = nc.location_id
    left join customer_spend_stats css        on si.location_id = css.location_id
    left join returning_rate rr               on si.location_id = rr.location_id
    left join loyalty_member_rate lmr         on si.location_id = lmr.location_id
    left join customer_concentration cc       on si.location_id = cc.location_id
    left join product_sales prs              on si.location_id = prs.location_id
    left join top_product_per_store tps       on si.location_id = tps.location_id
    left join avg_items_per_order aipo        on si.location_id = aipo.location_id
    left join labor lab                       on si.location_id = lab.location_id
    left join labor_cost_pct lcp              on si.location_id = lcp.location_id
    left join employees emp                   on si.location_id = emp.location_id
    left join inventory_current inv           on si.location_id = inv.location_id
    left join waste w                         on si.location_id = w.location_id
    left join waste_pct wp                    on si.location_id = wp.location_id
    left join top_wasted tw                   on si.location_id = tw.location_id
    left join pnl                             on si.location_id = pnl.location_id
    left join cost_per_order cpo              on si.location_id = cpo.location_id
    left join equipment eqp                   on si.location_id = eqp.location_id
    left join maintenance mnt                 on si.location_id = mnt.location_id
    left join peak_hour ph                    on si.location_id = ph.location_id
    left join service_speed ss                on si.location_id = ss.location_id
    left join health h                        on si.location_id = h.location_id
    left join met_revenue metr               on si.location_id = metr.location_id
    left join rankings rnk                    on si.location_id = rnk.location_id

)

select * from final
