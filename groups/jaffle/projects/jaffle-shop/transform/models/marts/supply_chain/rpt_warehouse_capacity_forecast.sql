with

warehouses as (

    select * from {{ ref('dim_warehouses') }}

),

inventory_value as (

    select * from {{ ref('int_inventory_value_by_location') }}

),

current_utilization as (

    select
        location_id as warehouse_id,
        sum(current_quantity) as total_units_stored,
        count(distinct product_id) as distinct_products

    from inventory_value

    group by location_id

),

inventory_movements as (

    select * from {{ ref('fct_inventory_movements') }}

),

monthly_net_change as (

    select
        location_id as warehouse_id,
        {{ dbt.date_trunc('month', 'moved_at') }} as movement_month,
        sum(quantity) as net_quantity_change

    from inventory_movements

    group by location_id, {{ dbt.date_trunc('month', 'moved_at') }}

),

avg_monthly_growth as (

    select
        warehouse_id,
        avg(net_quantity_change) as avg_monthly_net_change,
        count(distinct movement_month) as months_of_data

    from monthly_net_change

    group by warehouse_id

),

capacity_forecast as (

    select
        warehouses.warehouse_id,
        warehouses.warehouse_name,
        warehouses.warehouse_type,
        warehouses.capacity_units,
        warehouses.is_active,
        coalesce(current_utilization.total_units_stored, 0) as current_units_stored,
        coalesce(current_utilization.distinct_products, 0) as distinct_products,
        case
            when warehouses.capacity_units > 0
                then coalesce(current_utilization.total_units_stored, 0) * 1.0
                    / warehouses.capacity_units
            else null
        end as current_utilization_rate,
        warehouses.capacity_units
            - coalesce(current_utilization.total_units_stored, 0)
            as remaining_capacity,
        coalesce(avg_monthly_growth.avg_monthly_net_change, 0) as avg_monthly_growth_units,
        avg_monthly_growth.months_of_data,
        case
            when coalesce(avg_monthly_growth.avg_monthly_net_change, 0) > 0
                and warehouses.capacity_units > coalesce(current_utilization.total_units_stored, 0)
                then (warehouses.capacity_units
                    - coalesce(current_utilization.total_units_stored, 0))
                    * 1.0 / avg_monthly_growth.avg_monthly_net_change
            else null
        end as months_until_full,
        case
            when coalesce(avg_monthly_growth.avg_monthly_net_change, 0) > 0
                and warehouses.capacity_units > coalesce(current_utilization.total_units_stored, 0)
                then {{ dbt.dateadd(
                    'month',
                    'cast((warehouses.capacity_units - coalesce(current_utilization.total_units_stored, 0)) / nullif(avg_monthly_growth.avg_monthly_net_change, 0) as integer)',
                    dbt.current_timestamp()
                ) }}
            else null
        end as estimated_full_date

    from warehouses

    left join current_utilization
        on warehouses.warehouse_id = current_utilization.warehouse_id

    left join avg_monthly_growth
        on warehouses.warehouse_id = avg_monthly_growth.warehouse_id

)

select * from capacity_forecast
