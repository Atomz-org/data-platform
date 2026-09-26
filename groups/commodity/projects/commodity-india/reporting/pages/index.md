---
title: commodity-india — Overview
queries:
  - metrics/mcx_commodity_turnover_inr.sql
  - metrics/mcx_commodity_volume_flagship_lots.sql
  - metrics/mcx_commodity_option_premium_turnover_inr.sql
  - metrics/mcx_commodity_option_notional_turnover_inr.sql
  - metrics/mcx_commodity_sessions.sql
  - metrics/mcx_commodity_mini_turnover_inr.sql
  - metrics/mcx_commodity_oi_value_inr.sql
  - metrics/mcx_commodity_put_oi_notional_inr.sql
  - metrics/mcx_commodity_call_oi_notional_inr.sql
  - metrics/mcx_commodity_log_return.sql
  - metrics/mcx_commodity_return_total.sql
  - metrics/mcx_commodity_return_days.sql
  - metrics/mcx_commodity_up_sessions.sql
  - metrics/mcx_commodity_close_var_total.sql
  - metrics/mcx_commodity_close_var_days.sql
  - metrics/mcx_commodity_parkinson_var_total.sql
  - metrics/mcx_commodity_parkinson_var_days.sql
  - metrics/mcx_commodity_gk_var_total.sql
  - metrics/mcx_commodity_gk_var_days.sql
  - metrics/mcx_commodity_rs_var_total.sql
  - metrics/mcx_commodity_rs_var_days.sql
  - metrics/mcx_commodity_rsi_total.sql
  - metrics/mcx_commodity_rsi_days.sql
  - metrics/mcx_commodity_roll_yield_total.sql
  - metrics/mcx_commodity_roll_yield_days.sql
  - metrics/mcx_commodity_contango_sessions.sql
  - metrics/mcx_commodity_backwardation_sessions.sql
  - metrics/mcx_commodity_premium_total.sql
  - metrics/mcx_commodity_premium_days.sql
  - metrics/mcx_turnover_inr.sql
  - metrics/mcx_volume_lots.sql
  - metrics/mcx_session_days.sql
  - metrics/mcx_realised_vol_total.sql
  - metrics/mcx_realised_vol_days.sql
  - metrics/mcx_rsi_total.sql
  - metrics/mcx_rsi_days.sql
  - metrics/mcx_return_total.sql
  - metrics/mcx_premium_total.sql
  - metrics/mcx_premium_days.sql
  - metrics/mcx_gk_vol_30d_total.sql
  - metrics/mcx_gk_vol_30d_days.sql
  - metrics/mcx_parkinson_vol_30d_total.sql
  - metrics/mcx_parkinson_vol_30d_days.sql
  - metrics/mcx_rs_vol_30d_total.sql
  - metrics/mcx_rs_vol_30d_days.sql
  - metrics/mcx_roll_yield_total.sql
  - metrics/mcx_roll_yield_days.sql
  - metrics/mcx_contango_days.sql
  - metrics/mcx_backwardation_days.sql
  - metrics/signal_days.sql
  - metrics/range_position_total.sql
  - metrics/range_position_days.sql
  - metrics/realised_vol_total.sql
  - metrics/realised_vol_days.sql
  - metrics/momentum_20d_total.sql
  - metrics/momentum_20d_days.sql
  - metrics/attribution_days.sql
  - metrics/fx_share_total.sql
  - metrics/fx_share_days.sql
  - metrics/fx_contribution_total.sql
  - metrics/benchmark_contribution_total.sql
  - metrics/duty_contribution_total.sql
  - metrics/benchmark_price_usd_total.sql
  - metrics/benchmark_price_days.sql
  - metrics/landed_price_local_total.sql
  - metrics/landed_price_days.sql
  - metrics/duty_local_total.sql
  - metrics/usd_fx_rate_total.sql
  - metrics/period_high_price_usd.sql
  - metrics/period_low_price_usd.sql
  - metrics/contracts_traded.sql
  - metrics/mcx_commodity_mini_turnover_share.sql
  - metrics/mcx_commodity_put_call_ratio.sql
  - metrics/mcx_commodity_avg_daily_return.sql
  - metrics/mcx_commodity_hit_rate.sql
  - metrics/mcx_commodity_close_variance.sql
  - metrics/mcx_commodity_parkinson_variance.sql
  - metrics/mcx_commodity_gk_variance.sql
  - metrics/mcx_commodity_rs_variance.sql
  - metrics/mcx_commodity_avg_rsi.sql
  - metrics/mcx_commodity_avg_roll_yield.sql
  - metrics/mcx_commodity_contango_share.sql
  - metrics/mcx_commodity_backwardation_share.sql
  - metrics/mcx_commodity_avg_premium_to_landed.sql
  - metrics/avg_mcx_realised_vol.sql
  - metrics/avg_mcx_rsi.sql
  - metrics/avg_mcx_daily_return.sql
  - metrics/avg_mcx_premium_to_landed.sql
  - metrics/avg_mcx_garman_klass_vol_30d.sql
  - metrics/avg_mcx_parkinson_vol_30d.sql
  - metrics/avg_mcx_rogers_satchell_vol_30d.sql
  - metrics/avg_mcx_roll_yield.sql
  - metrics/mcx_contango_share.sql
  - metrics/avg_range_position.sql
  - metrics/avg_realised_vol.sql
  - metrics/avg_momentum_20d.sql
  - metrics/avg_fx_share_of_move.sql
  - metrics/avg_benchmark_price_usd.sql
  - metrics/avg_landed_price_local.sql
  - metrics/avg_duty_local.sql
  - metrics/avg_usd_fx_rate.sql
---

Every number on this page is a governed metric compiled from the dbt
semantic layer into `queries/metrics/`. Nothing here restates business
logic — if a figure you need is missing, the fix is a metric definition,
not SQL in this page.

```sql date_bounds
-- DateRange reads min()/max() from ONE column, so both bounds must
-- arrive as two rows in that column — not two columns of one row.
select min(metric_time) as metric_time from ${metrics_mcx_commodity_volume_flagship_lots}
union all
select max(metric_time) from ${metrics_mcx_commodity_volume_flagship_lots}
```

<DateRange name=period data={date_bounds} dates=metric_time/>

```sql kpi_mcx_commodity_volume_flagship_lots
select sum(mcx_commodity_volume_flagship_lots) as mcx_commodity_volume_flagship_lots
from ${metrics_mcx_commodity_volume_flagship_lots}
```

```sql kpi_mcx_commodity_option_premium_turnover_inr
select sum(mcx_commodity_option_premium_turnover_inr) as mcx_commodity_option_premium_turnover_inr
from ${metrics_mcx_commodity_option_premium_turnover_inr}
```

```sql kpi_mcx_commodity_option_notional_turnover_inr
select sum(mcx_commodity_option_notional_turnover_inr) as mcx_commodity_option_notional_turnover_inr
from ${metrics_mcx_commodity_option_notional_turnover_inr}
```

```sql kpi_mcx_commodity_oi_value_inr
select sum(mcx_commodity_oi_value_inr) as mcx_commodity_oi_value_inr
from ${metrics_mcx_commodity_oi_value_inr} where metric_time = (select max(metric_time) from ${metrics_mcx_commodity_oi_value_inr})
```

<Grid cols=4>

<BigValue data={kpi_mcx_commodity_volume_flagship_lots} value=mcx_commodity_volume_flagship_lots title='Volume (flagship-lot equivalents) — per Commodity' fmt='#,##0.0,,"M"'/>
<BigValue data={kpi_mcx_commodity_option_premium_turnover_inr} value=mcx_commodity_option_premium_turnover_inr title='Options Premium Turnover (₹) — per Commodity' fmt='"₹"#,##0.00,,,,"T"'/>
<BigValue data={kpi_mcx_commodity_option_notional_turnover_inr} value=mcx_commodity_option_notional_turnover_inr title='Options Notional Turnover (₹) — per Commodity' fmt='"₹"#,##0.00,,,,"T"'/>
<BigValue data={kpi_mcx_commodity_oi_value_inr} value=mcx_commodity_oi_value_inr title='Open Interest Value (₹) — per Commodity' fmt='"₹"#,##0.0,,,"B"'/>

</Grid>

## Volume (flagship-lot equivalents) — per Commodity over time

```sql trend
select metric_time, sum(mcx_commodity_volume_flagship_lots) as mcx_commodity_volume_flagship_lots
from ${metrics_mcx_commodity_volume_flagship_lots}
group by 1 order by 1
```

<LineChart data={trend} x=metric_time y=mcx_commodity_volume_flagship_lots yFmt=num0/>

## Volume (flagship-lot equivalents) — per Commodity by mcx commodity

```sql breakdown
select mcx_commodity, sum(mcx_commodity_volume_flagship_lots) as mcx_commodity_volume_flagship_lots
from ${metrics_mcx_commodity_volume_flagship_lots}
where mcx_commodity is not null
group by 1 order by 2 desc
```

<BarChart data={breakdown} x=mcx_commodity y=mcx_commodity_volume_flagship_lots swapXY=true xFmt=num0/>

## Detail

<DataTable data={breakdown} rows=15/>

---

_Generated by `pf report build`. Metric definitions live in
`transform/models/semantic/`; this page is a projection of them._
