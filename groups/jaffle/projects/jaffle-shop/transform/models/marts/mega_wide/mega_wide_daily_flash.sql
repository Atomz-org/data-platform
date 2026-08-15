{{
    config(
        materialized='table',
        tags=['mega_wide', 'daily_flash']
    )
}}

/*
    mega_wide_daily_flash
    ---------------------
    One row per calendar day. Aggregates revenue, customers, labor, inventory,
    financial, marketing, and operations metrics from every domain model.
    Designed for BI flash-report consumption (80+ columns).
*/

with

o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

lcd as (
    select * from {{ ref('int_labor_cost_daily') }}
),

we as (
    select * from {{ ref('fct_waste_events') }}
),

im as (
    select * from {{ ref('fct_inventory_movements') }}
),

fe as (
    select * from {{ ref('fct_expenses') }}
),

fr as (
    select * from {{ ref('fct_refunds') }}
),

msd as (
    select * from {{ ref('int_marketing_spend_daily') }}
),

lt as (
    select * from {{ ref('fct_loyalty_transactions') }}
),

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

ee as (
    select * from {{ ref('stg_email_events') }}
),

me as (
    select * from {{ ref('fct_maintenance_events') }}
),


date_spine as (

    select
        date_day
    from {{ ref('util_date_spine') }}

),

date_dimensions as (

    select
        date_day,
        {{ day_of_week_number('date_day') }}                                          as day_of_week,
        dayname(date_day)                                                     as day_name,
        {{ sf_date_trunc('week', "date_day") }}::date                                  as week_start,
        {{ sf_date_trunc('month', "date_day") }}::date                                 as month_start,
        {{ sf_date_trunc('quarter', "date_day") }}::date                               as quarter_start,
        extract(year from date_day)::int                                    as year,
        case when {{ day_of_week_number('date_day') }} in (0, 6) then true else false end as is_weekend
    from date_spine

),

-- ============================================================
-- Revenue / Order CTEs
-- ============================================================
orders_base as (

    select
        o.ordered_at::date                                                  as date_day,
        o.order_id,
        o.customer_id,
        o.location_id,
        o.order_total
    from o
    where o.ordered_at is not null

),

order_items_base as (

    select
        o.ordered_at::date                                                  as date_day,
        oi.order_id,
        oi.product_id,
        p.product_type,
        1                                                                   as quantity,
        coalesce(s.supply_cost, 0)                                          as supply_cost,
        p.product_price                                                     as item_revenue,
        p.product_price
    from oi
    inner join o on oi.order_id = o.order_id
    inner join p on oi.product_id = p.product_id
    left join (
        select product_id, sum(supply_cost) as supply_cost
        from {{ ref('stg_supplies') }}
        group by product_id
    ) s on oi.product_id = s.product_id

),

daily_revenue as (

    select
        revenue_date,
        total_revenue,
        invoice_count as order_count
    from {{ ref('int_daily_revenue') }}

),

revenue_metrics as (

    select
        ob.date_day,
        count(distinct ob.order_id)                                         as total_orders,
        coalesce(sum(ob.order_total), 0)                                    as total_revenue,
        avg(ob.order_total)                                                 as avg_order_value,
        percentile_cont(0.5) within group (order by ob.order_total)         as median_order_value_proxy,
        min(ob.order_total)                                                 as min_order_value,
        max(ob.order_total)                                                 as max_order_value,
        count(distinct ob.customer_id)                                      as unique_customers,
        count(distinct ob.location_id)                                      as stores_with_orders
    from orders_base ob
    group by 1

),

item_metrics as (

    select
        oib.date_day,
        sum(oib.quantity)                                                   as total_items_sold,
        count(distinct oib.product_id)                                      as unique_products_sold,
        sum(case when oib.product_type = 'food' then oib.item_revenue else 0 end)      as food_revenue,
        sum(case when oib.product_type = 'beverage' then oib.item_revenue else 0 end)  as beverage_revenue,
        avg(oib.item_revenue - oib.supply_cost)                             as avg_product_margin,
        max(oib.item_revenue)                                               as top_product_revenue,
        min(oib.item_revenue)                                               as bottom_product_revenue
    from order_items_base oib
    group by 1

),

-- ============================================================
-- Customer CTEs
-- ============================================================
customer_first_order as (

    select
        customer_id,
        min(ordered_at::date)                                               as first_order_date
    from {{ ref('stg_orders') }}
    group by 1

),

customer_daily as (

    select
        ob.date_day,
        count(distinct case when cfo.first_order_date = ob.date_day then ob.customer_id end) as new_customers,
        count(distinct case when cfo.first_order_date < ob.date_day then ob.customer_id end) as returning_customers,
        count(distinct ob.customer_id)                                      as unique_customers_check,
        max(ob.order_total)                                                 as max_spend_customer,
        avg(ob.order_total)                                                 as avg_spend_per_customer
    from orders_base ob
    left join customer_first_order cfo on ob.customer_id = cfo.customer_id
    group by 1

),

customer_new_returning_revenue as (

    select
        ob.date_day,
        sum(case when cfo.first_order_date = ob.date_day then ob.order_total else 0 end)    as new_customer_revenue,
        sum(case when cfo.first_order_date < ob.date_day then ob.order_total else 0 end)     as returning_customer_revenue
    from orders_base ob
    left join customer_first_order cfo on ob.customer_id = cfo.customer_id
    group by 1

),

repeat_customers_daily as (

    select
        ob.date_day,
        count(distinct case when cfo.first_order_date < ob.date_day then ob.customer_id end) as repeat_purchase_customers
    from orders_base ob
    left join customer_first_order cfo on ob.customer_id = cfo.customer_id
    group by 1

),

-- ============================================================
-- Product mix
-- ============================================================
order_product_types as (

    select
        oib.date_day,
        oib.order_id,
        max(case when oib.product_type = 'food' then true else false end)   as has_food,
        max(case when oib.product_type = 'beverage' then true else false end) as has_beverage,
        count(distinct oib.product_id)                                      as items_in_order
    from order_items_base oib
    group by 1, 2

),

product_mix_daily as (

    select
        date_day,
        count(case when has_food and not has_beverage then 1 end)           as food_orders,
        count(case when has_beverage and not has_food then 1 end)           as drink_orders,
        count(case when has_food and has_beverage then 1 end)               as mixed_orders,
        avg(items_in_order)                                                 as avg_items_per_order
    from order_product_types
    group by 1

),

-- ============================================================
-- Labor
-- ============================================================
labor_daily as (

    select
        lcd.work_date,
        coalesce(sum(lcd.total_hours), 0)                             as total_labor_hours,
        coalesce(sum(lcd.total_labor_cost), 0)                              as total_labor_cost,
        coalesce(sum(lcd.employee_count), 0)                                as employees_working
    from lcd
    group by 1

),

-- ============================================================
-- Inventory & Waste
-- ============================================================
waste_daily as (

    select
        cast(we.wasted_at as date)                                                       as date_day,
        count(*)                                                            as waste_event_count,
        coalesce(sum(we.cost_of_waste), 0)                                     as waste_cost
    from we
    group by 1

),

inventory_daily as (

    select
        cast(im.moved_at as date)                                                    as date_day,
        sum(case when im.movement_type = 'inbound' then im.quantity else 0 end)     as inbound_units,
        sum(case when im.movement_type = 'outbound' then im.quantity else 0 end)    as outbound_units,
        sum(case when im.movement_type = 'inbound' then im.quantity else 0 end)
            - sum(case when im.movement_type = 'outbound' then im.quantity else 0 end) as net_inventory_change,
        count(distinct case when im.quantity = 0 then im.product_id end)    as stockout_product_count_proxy,
        count(*)                                                            as inventory_movement_count
    from im
    group by 1

),

-- ============================================================
-- Financial
-- ============================================================
expenses_daily as (

    select
        fe.incurred_date                                                     as date_day,
        coalesce(sum(fe.expense_amount), 0)                                         as total_expenses,
        count(distinct fe.location_id)                                      as stores_with_expenses
    from fe
    group by 1

),

refunds_daily as (

    select
        fr.requested_date                                                      as date_day,
        count(*)                                                            as refund_count,
        coalesce(sum(fr.refund_amount), 0)                                  as refund_amount
    from fr
    group by 1

),

-- ============================================================
-- Marketing
-- ============================================================
marketing_daily as (

    select
        msd.spend_date,
        coalesce(sum(msd.channel_spend), 0)                                         as campaign_spend
    from msd
    group by 1

),

loyalty_daily as (

    select
        lt.transacted_at                                                 as date_day,
        count(*)                                                            as loyalty_transaction_count,
        sum(case when lt.transaction_type = 'earn' then lt.points else 0 end)       as loyalty_points_issued,
        sum(case when lt.transaction_type = 'redeem' then lt.points else 0 end)     as loyalty_points_redeemed,
        count(distinct case when lt.transaction_type = 'signup' then lt.customer_id end) as new_loyalty_signups,
        count(distinct lt.customer_id)                                      as loyalty_customers_active,
        sum(case when lt.transaction_type = 'gift_card' then 1 else 0 end)  as gift_card_transactions
    from lt
    group by 1

),

coupon_daily as (

    select
        cast(cr.redeemed_at as date)                                                  as date_day,
        count(*)                                                            as coupon_redemption_count,
        coalesce(sum(cr.discount_applied), 0)                                as coupon_discount_given
    from cr
    group by 1

),

email_daily as (

    select
        ee.event_date                                                       as date_day,
        sum(case when ee.email_event_type = 'send' then 1 else 0 end)            as email_sends,
        sum(case when ee.email_event_type = 'open' then 1 else 0 end)            as email_opens
    from ee
    group by 1

),

-- ============================================================
-- Operations
-- ============================================================
maintenance_daily as (

    select
        cast(me.scheduled_date as date)                                                       as date_day,
        count(*)                                                            as maintenance_event_count,
        coalesce(sum(me.maintenance_cost), 0)                                           as maintenance_cost,
        count(distinct me.equipment_id)                                     as equipment_affected_count
    from me
    group by 1

),

-- ============================================================
-- Loyalty-order join for loyalty / non-loyalty split
-- ============================================================
loyalty_orders_daily as (

    select
        ob.date_day,
        count(distinct case when lt.customer_id is not null then ob.order_id end) as loyalty_customer_orders,
        count(distinct case when lt.customer_id is null then ob.order_id end)     as non_loyalty_orders,
        count(distinct case when cr.order_id is not null then ob.customer_id end) as customers_with_coupon
    from orders_base ob
    left join (
        select distinct customer_id
        from {{ ref('fct_loyalty_transactions') }}
    ) lt on ob.customer_id = lt.customer_id
    left join cr on ob.order_id = cr.order_id
    group by 1

),

-- ============================================================
-- Location helper
-- ============================================================
location_count as (

    select count(*) as total_locations
    from {{ ref('stg_locations') }}

),

-- ============================================================
-- Join everything onto the date spine
-- ============================================================
joined as (

    select
        -- ── Date dimensions (8) ──────────────────────────────────
        dd.date_day,
        dd.day_of_week,
        dd.day_name,
        dd.week_start,
        dd.month_start,
        dd.quarter_start,
        dd.year,
        dd.is_weekend,

        -- ── Revenue (12) ─────────────────────────────────────────
        coalesce(rm.total_revenue, 0)                                       as total_revenue,
        coalesce(rm.total_orders, 0)                                        as total_orders,
        rm.avg_order_value,
        rm.median_order_value_proxy,
        rm.min_order_value,
        rm.max_order_value,
        coalesce(im2.total_items_sold, 0)                                   as total_items_sold,
        coalesce(im2.food_revenue, 0)                                       as food_revenue,
        coalesce(im2.beverage_revenue, 0)                                   as beverage_revenue,
        coalesce(cnrr.new_customer_revenue, 0)                              as new_customer_revenue,
        coalesce(cnrr.returning_customer_revenue, 0)                        as returning_customer_revenue,
        case when rm.total_revenue is not null and rm.stores_with_orders > 0
             then rm.total_revenue / rm.stores_with_orders
             else 0
        end                                                                 as revenue_per_store_avg,

        -- ── Customer (10) ────────────────────────────────────────
        coalesce(rm.unique_customers, 0)                                    as unique_customers,
        coalesce(cd.new_customers, 0)                                       as new_customers,
        coalesce(cd.returning_customers, 0)                                 as returning_customers,
        case when coalesce(rm.unique_customers, 0) > 0
             then round(cd.new_customers::numeric / rm.unique_customers * 100, 2)
             else 0
        end                                                                 as pct_new_customers,
        cd.avg_spend_per_customer,
        cd.max_spend_customer,
        coalesce(lod.loyalty_customer_orders, 0)                            as loyalty_customer_orders,
        coalesce(lod.non_loyalty_orders, 0)                                 as non_loyalty_orders,
        coalesce(lod.customers_with_coupon, 0)                              as customers_with_coupon,
        coalesce(rcd.repeat_purchase_customers, 0)                          as repeat_purchase_customers,

        -- ── Product (8) ──────────────────────────────────────────
        coalesce(im2.unique_products_sold, 0)                               as unique_products_sold,
        pmd.avg_items_per_order,
        coalesce(pmd.food_orders, 0)                                        as food_orders,
        coalesce(pmd.drink_orders, 0)                                       as drink_orders,
        coalesce(pmd.mixed_orders, 0)                                       as mixed_orders,
        im2.top_product_revenue,
        im2.bottom_product_revenue,
        im2.avg_product_margin,

        -- ── Labor (10) ──────────────────────────────────────────
        coalesce(ld.total_labor_hours, 0)                                   as total_labor_hours,
        coalesce(ld.total_labor_cost, 0)                                    as total_labor_cost,
        case when coalesce(rm.total_revenue, 0) > 0
             then round(ld.total_labor_cost::numeric / rm.total_revenue * 100, 2)
             else 0
        end                                                                 as labor_cost_pct_revenue,
        coalesce(ld.employees_working, 0)                                   as employees_working,
        case when coalesce(ld.total_labor_hours, 0) > 0
             then round(rm.total_orders::numeric / ld.total_labor_hours, 2)
             else 0
        end                                                                 as orders_per_labor_hour,
        0 as overtime_pct,

        -- ── Inventory (8) ───────────────────────────────────────
        coalesce(wd.waste_event_count, 0)                                   as waste_event_count,
        coalesce(wd.waste_cost, 0)                                          as waste_cost,
        coalesce(invd.inbound_units, 0)                                     as inbound_units,
        coalesce(invd.outbound_units, 0)                                    as outbound_units,
        coalesce(invd.net_inventory_change, 0)                              as net_inventory_change,
        coalesce(invd.stockout_product_count_proxy, 0)                      as stockout_product_count_proxy,
        coalesce(invd.inventory_movement_count, 0)                          as inventory_movement_count,
        case when coalesce(rm.total_revenue, 0) > 0
             then round(wd.waste_cost::numeric / rm.total_revenue * 100, 2)
             else 0
        end                                                                 as waste_pct_revenue,

        -- ── Financial (10) ──────────────────────────────────────
        coalesce(ed.total_expenses, 0)                                      as total_expenses,
        coalesce(rm.total_revenue, 0) - coalesce(ed.total_expenses, 0)
            - coalesce(ld.total_labor_cost, 0)                              as gross_profit_proxy,
        coalesce(rd.refund_count, 0)                                        as refund_count,
        coalesce(rd.refund_amount, 0)                                       as refund_amount,
        coalesce(loyld.gift_card_transactions, 0)                           as gift_card_transactions,
        coalesce(rm.total_revenue, 0)
            - coalesce(ed.total_expenses, 0)
            - coalesce(ld.total_labor_cost, 0)
            - coalesce(rd.refund_amount, 0)                                 as net_cash_flow_proxy,
        case when coalesce(rm.total_revenue, 0) > 0
             then round(ed.total_expenses::numeric / rm.total_revenue * 100, 2)
             else 0
        end                                                                 as expense_pct_revenue,
        case when coalesce(ed.stores_with_expenses, 0) > 0
             then round(ed.total_expenses::numeric / ed.stores_with_expenses, 2)
             else 0
        end                                                                 as avg_expense_per_store,
        coalesce(cpd.coupon_discount_given, 0)                              as coupon_discount_total,
        round(coalesce(rm.total_revenue, 0) * 0.08, 2)           as tax_collected_proxy,

        -- ── Marketing (8) ───────────────────────────────────────
        coalesce(mkd.campaign_spend, 0)                                     as campaign_spend,
        coalesce(cpd.coupon_redemption_count, 0)                            as coupon_redemption_count,
        coalesce(cpd.coupon_discount_given, 0)                              as coupon_discount_given,
        coalesce(loyld.loyalty_points_issued, 0)                            as loyalty_points_issued,
        coalesce(loyld.loyalty_points_redeemed, 0)                          as loyalty_points_redeemed,
        coalesce(emd.email_sends, 0)                                        as email_sends,
        coalesce(emd.email_opens, 0)                                        as email_opens,
        coalesce(loyld.new_loyalty_signups, 0)                              as new_loyalty_signups,

        -- ── Operations (6) ──────────────────────────────────────
        coalesce(mtd.maintenance_event_count, 0)                            as maintenance_event_count,
        coalesce(mtd.maintenance_cost, 0)                                   as maintenance_cost,
        coalesce(mtd.equipment_affected_count, 0)                           as equipment_affected_count,
        round((coalesce(rm.total_orders, 0) * 0.15))               as delivery_count_proxy,
        coalesce(rm.stores_with_orders, 0)                                  as stores_with_orders,
        {{ sf_greatest(["(lc.total_locations - coalesce(rm.stores_with_orders, 0))", "0"]) }} as stores_without_orders

    from date_dimensions dd
    left join revenue_metrics rm              on dd.date_day = rm.date_day
    left join item_metrics im2                on dd.date_day = im2.date_day
    left join customer_daily cd               on dd.date_day = cd.date_day
    left join customer_new_returning_revenue cnrr on dd.date_day = cnrr.date_day
    left join repeat_customers_daily rcd      on dd.date_day = rcd.date_day
    left join product_mix_daily pmd           on dd.date_day = pmd.date_day
    left join labor_daily ld                  on dd.date_day = ld.work_date
    left join waste_daily wd                  on dd.date_day = wd.date_day
    left join inventory_daily invd            on dd.date_day = invd.date_day
    left join expenses_daily ed               on dd.date_day = ed.date_day
    left join refunds_daily rd                on dd.date_day = rd.date_day
    left join marketing_daily mkd             on dd.date_day = mkd.spend_date
    left join loyalty_daily loyld             on dd.date_day = loyld.date_day
    left join coupon_daily cpd                on dd.date_day = cpd.date_day
    left join email_daily emd                 on dd.date_day = emd.date_day
    left join maintenance_daily mtd           on dd.date_day = mtd.date_day
    left join loyalty_orders_daily lod        on dd.date_day = lod.date_day
    cross join location_count lc

),

-- ============================================================
-- Trend / window calculations
-- ============================================================
with_trends as (

    select
        j.*,

        -- ── Trend comparisons (10) ──────────────────────────────
        avg(j.total_revenue) over (
            order by j.date_day rows between 6 preceding and current row
        )                                                                   as revenue_7d_avg,

        avg(j.total_revenue) over (
            order by j.date_day rows between 27 preceding and current row
        )                                                                   as revenue_28d_avg,

        case when avg(j.total_revenue) over (
                order by j.date_day rows between 6 preceding and current row
             ) > 0
             then round(
                (j.total_revenue - avg(j.total_revenue) over (
                    order by j.date_day rows between 6 preceding and current row
                )) / avg(j.total_revenue) over (
                    order by j.date_day rows between 6 preceding and current row
                ) * 100, 2)
             else 0
        end                                                                 as revenue_vs_7d_avg_pct,

        case when avg(j.total_revenue) over (
                order by j.date_day rows between 27 preceding and current row
             ) > 0
             then round(
                (j.total_revenue - avg(j.total_revenue) over (
                    order by j.date_day rows between 27 preceding and current row
                )) / avg(j.total_revenue) over (
                    order by j.date_day rows between 27 preceding and current row
                ) * 100, 2)
             else 0
        end                                                                 as revenue_vs_28d_avg_pct,

        avg(j.total_orders) over (
            order by j.date_day rows between 6 preceding and current row
        )                                                                   as orders_7d_avg,

        case when avg(j.total_orders) over (
                order by j.date_day rows between 6 preceding and current row
             ) > 0
             then round(
                (j.total_orders - avg(j.total_orders) over (
                    order by j.date_day rows between 6 preceding and current row
                )) / avg(j.total_orders) over (
                    order by j.date_day rows between 6 preceding and current row
                ) * 100, 2)
             else 0
        end                                                                 as orders_vs_7d_avg_pct,

        avg(j.unique_customers) over (
            order by j.date_day rows between 6 preceding and current row
        )                                                                   as customers_7d_avg,

        -- Anomaly: revenue deviates more than 2 std-devs from 28-day mean
        case when abs(j.total_revenue - avg(j.total_revenue) over (
                order by j.date_day rows between 27 preceding and current row
             )) > 2 * coalesce(nullif(stddev(j.total_revenue) over (
                order by j.date_day rows between 27 preceding and current row
             ), 0), 1)
             then true else false
        end                                                                 as is_revenue_anomaly,

        case when abs(j.total_orders - avg(j.total_orders) over (
                order by j.date_day rows between 27 preceding and current row
             )) > 2 * coalesce(nullif(stddev(j.total_orders) over (
                order by j.date_day rows between 27 preceding and current row
             ), 0), 1)
             then true else false
        end                                                                 as is_order_anomaly,

        j.total_revenue - coalesce(lag(j.total_revenue) over (order by j.date_day), 0)
                                                                            as day_over_day_revenue_change

    from joined j

)

select * from with_trends
order by date_day
