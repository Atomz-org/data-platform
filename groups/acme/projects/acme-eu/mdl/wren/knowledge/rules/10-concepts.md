# Concepts

What each model is an instance of, and how a row is identified.

| model | concept | identity | meaning |
|---|---|---|---|
| `dim_customers` | Payment | payment_id | Movement of money settling an agreement. |
| `fct_payments` | Customer | id | A party that buys. May be a person or an organization. |
| `fct_revenue` | — | — |  |

## Column roles

Every column carries `pf.role` in the manifest. What a role means for a query:

| role | rule |
|---|---|
| `event_time` | the time axis; the default for any trend or period |
| `foreign_key` | a join to another model along a declared relationship |
| `money_amount` | additive within one currency; the sibling currency_code says which |
| `natural_key` | identity of the row; count it, never sum it |
