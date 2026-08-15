with

touchpoints as (

    select
        customer_id,
        touchpoint_date,
        channel,
        campaign_id,
        touchpoint_sequence
    from {{ ref('mkt_customer_journey_touchpoints') }}

),

orders as (

    select
        customer_id,
        order_id,
        ordered_at,
        order_total
    from {{ ref('stg_orders') }}

),

-- Match touchpoints to subsequent orders
touch_to_order as (

    select
        t.customer_id,
        t.touchpoint_date,
        t.channel,
        t.campaign_id,
        o.order_id,
        o.order_total,
        o.ordered_at,
        count(*) over (
            partition by o.order_id, t.customer_id
        ) as touches_before_order
    from touchpoints as t
    inner join orders as o
        on t.customer_id = o.customer_id
        and t.touchpoint_date <= o.ordered_at
        and {{ dbt.datediff('t.touchpoint_date', 'o.ordered_at', 'day') }} <= 30

),

-- Linear attribution: equal credit to each touchpoint
attributed as (

    select
        customer_id,
        channel,
        campaign_id,
        order_id,
        order_total,
        touches_before_order,
        case
            when touches_before_order > 0
            then order_total / touches_before_order
            else 0
        end as attributed_revenue_linear,
        -- First touch gets 40%, last gets 40%, rest split 20%
        case
            when row_number() over (partition by order_id order by touchpoint_date) = 1
            then order_total * 0.40
            when row_number() over (partition by order_id order by touchpoint_date desc) = 1
            then order_total * 0.40
            when touches_before_order > 2
            then order_total * 0.20 / (touches_before_order - 2)
            else 0
        end as attributed_revenue_position
    from touch_to_order

),

final as (

    select
        channel,
        campaign_id,
        count(distinct order_id) as attributed_orders,
        sum(attributed_revenue_linear) as linear_attributed_revenue,
        sum(attributed_revenue_position) as position_attributed_revenue,
        count(*) as total_touchpoints
    from attributed
    group by 1, 2

)

select * from final
