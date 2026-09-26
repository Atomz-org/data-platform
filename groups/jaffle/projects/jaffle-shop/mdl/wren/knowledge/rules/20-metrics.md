# Metrics

## Cube `jaffle_shop_core` on `orders`

Ask it with `wren cube query --cube <name> --measures <m> --dimensions <d>`; the
engine writes the GROUP BY.

Measures:

| measure | expression | meaning |
|---|---|---|
| `drink_orders` | `sum(1)` | Drink Orders |
| `drink_revenue` | `sum(case when is_drink_item then product_price else 0 end)` | Drink Revenue |
| `drink_revenue_pct` | `sum(case when is_drink_item then product_price else 0 end) / nullif(sum(product_price), 0)` | Drink Revenue % |
| `food_orders` | `sum(1)` | Food Orders |
| `food_revenue` | `sum(case when is_food_item then product_price else 0 end)` | Food Revenue |
| `food_revenue_pct` | `sum(case when is_food_item then product_price else 0 end) / nullif(sum(product_price), 0)` | Food Revenue % |
| `large_orders` | `sum(1)` | Large Orders |
| `median_revenue` | `percentile_cont(0.5) within group (order by product_price)` | Median Revenue |
| `new_customer_orders` | `sum(1)` | New Customers |
| `order_cost` | `sum(orders.order_cost)` | Order Cost |
| `order_total` | `sum(orders.order_total)` | Order Total |
| `orders` | `sum(1)` | Orders |
| `revenue` | `sum(product_price)` | Revenue |

Dimensions: `customer_name`, `customer_order_number`, `customer_type`, `is_drink_item`, `is_drink_order`, `is_food_item`, `is_food_order`, `is_perishable_supply`, `location_name`, `order_total_dim`, `product_description`, `product_id`, `product_name`, `product_price`, `product_type`, `supply_cost`, `supply_id`, `supply_name`
Time dimensions: `first_ordered_at`, `last_ordered_at`, `opened_date`, `ordered_at`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `average_order_value` | derived | `customers` | `derived` |  |  | LTV pre-tax / number of orders |
| `count_lifetime_orders` | simple | `customers` | `sum(count_lifetime_orders)` |  |  | Count of lifetime orders |
| `cumulative_revenue` | cumulative | `order_items` | `sum(product_price)` |  |  | The cumulative revenue for all orders. |
| `drink_orders` | simple | `orders` | `sum(1)` |  | is_drink_order = true | Count of orders that contain drink order items |
| `drink_revenue` | simple | `order_items` | `sum(case when is_drink_item then product_price else 0 end)` |  |  | The revenue from drinks in each order |
| `drink_revenue_pct` | ratio | `order_items` | `drink_revenue / revenue` |  |  | The % of order revenue from drinks. |
| `food_orders` | simple | `orders` | `sum(1)` |  | is_food_order = true | Count of orders that contain food order items |
| `food_revenue` | simple | `order_items` | `sum(case when is_food_item then product_price else 0 end)` |  |  | The revenue from food in each order |
| `food_revenue_pct` | ratio | `order_items` | `food_revenue / revenue` |  |  | The % of order revenue from food. |
| `large_orders` | simple | `orders` | `sum(1)` |  | order_total_dim >= 20 | Count of orders with order total over 20. |
| `lifetime_spend_pretax` | simple | `customers` | `sum(lifetime_spend_pretax)` |  |  | Customer's lifetime spend before tax |
| `median_revenue` | simple | `order_items` | `percentile_cont(0.5) within group (order by product_price)` |  |  | The median revenue for each order item. Excludes tax. |
| `new_customer_orders` | simple | `orders` | `sum(1)` |  | customer_order_number = 1 | New customer's first order count |
| `order_cost` | simple | `orders` | `sum(order_cost)` |  |  | Sum of cost for each order item. |
| `order_gross_profit` | derived | `orders` | `derived` |  |  | Gross profit from each order. |
| `order_total` | simple | `orders` | `sum(order_total)` |  |  | Sum of total order amonunt. Includes tax + revenue. |
| `orders` | simple | `orders` | `sum(1)` |  |  | Count of orders. |
| `revenue` | simple | `order_items` | `sum(product_price)` |  |  | Sum of the product revenue for each order item. Excludes tax. |
| `revenue_growth_mom` | derived | `order_items` | `derived` |  |  | Percentage growth of revenue compared to 1 month ago. Excluded tax |
