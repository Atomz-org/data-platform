with supplier_base as (
    select
        supplier_id,
        supplier_name,
        is_active
    from {{ ref('dim_suppliers') }}
),

spend_data as (
    select
        supplier_id,
        total_spend,
        order_month
    from {{ ref('int_supplier_spend_monthly') }}
),

supplier_total_spend as (
    select
        supplier_id,
        sum(total_spend) as total_spend,
        count(distinct order_month) as active_months,
        avg(total_spend) as avg_monthly_spend
    from spend_data
    group by supplier_id
),

-- Concentration risk: what % of total procurement does each supplier represent
concentration as (
    select
        supplier_id,
        total_spend,
        round(
            cast(total_spend as {{ dbt.type_float() }})
            / nullif(sum(total_spend) over (), 0) * 100, 2
        ) as spend_concentration_pct,
        rank() over (order by total_spend desc) as spend_rank
    from supplier_total_spend
),

lead_times as (
    select
        supplier_id,
        avg_lead_time_days,
        avg_lead_time_variance_days,
        min_lead_time_days,
        max_lead_time_days
    from {{ ref('int_lead_time_by_supplier') }}
),

quality as (
    select
        supplier_id,
        quality_score,
        defect_rate
    from {{ ref('int_supplier_quality_score') }}
)

select
    sb.supplier_id,
    sb.supplier_name,
    sb.is_active,

    -- Spend & concentration
    coalesce(sts.total_spend, 0) as total_spend,
    coalesce(sts.avg_monthly_spend, 0) as avg_monthly_spend,
    coalesce(con.spend_concentration_pct, 0) as spend_concentration_pct,
    con.spend_rank,

    -- Lead time
    coalesce(lt.avg_lead_time_days, 0) as avg_lead_time_days,
    coalesce(lt.avg_lead_time_variance_days, 0) as lead_time_variability,
    lt.min_lead_time_days,
    lt.max_lead_time_days,

    -- Quality
    coalesce(q.quality_score, 0) as quality_score,
    coalesce(q.defect_rate, 0) as defect_rate,

    -- Risk scoring (1-5 scale, 5 = highest risk)
    case
        when con.spend_concentration_pct >= 30 then 5
        when con.spend_concentration_pct >= 20 then 4
        when con.spend_concentration_pct >= 10 then 3
        when con.spend_concentration_pct >= 5 then 2
        else 1
    end as concentration_risk_score,

    case
        when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.5 then 5
        when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.3 then 4
        when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.2 then 3
        when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.1 then 2
        else 1
    end as reliability_risk_score,

    case
        when q.quality_score < 60 then 5
        when q.quality_score < 70 then 4
        when q.quality_score < 80 then 3
        when q.quality_score < 90 then 2
        else 1
    end as quality_risk_score,

    -- Composite risk
    round((
        case when con.spend_concentration_pct >= 30 then 5 when con.spend_concentration_pct >= 20 then 4 when con.spend_concentration_pct >= 10 then 3 when con.spend_concentration_pct >= 5 then 2 else 1 end
        + case when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.5 then 5 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.3 then 4 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.2 then 3 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.1 then 2 else 1 end
        + case when q.quality_score < 60 then 5 when q.quality_score < 70 then 4 when q.quality_score < 80 then 3 when q.quality_score < 90 then 2 else 1 end
    ) / 3.0, 2) as composite_risk_score,

    case
        when (
            case when con.spend_concentration_pct >= 30 then 5 when con.spend_concentration_pct >= 20 then 4 when con.spend_concentration_pct >= 10 then 3 when con.spend_concentration_pct >= 5 then 2 else 1 end
            + case when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.5 then 5 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.3 then 4 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.2 then 3 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.1 then 2 else 1 end
            + case when q.quality_score < 60 then 5 when q.quality_score < 70 then 4 when q.quality_score < 80 then 3 when q.quality_score < 90 then 2 else 1 end
        ) >= 12 then 'critical'
        when (
            case when con.spend_concentration_pct >= 30 then 5 when con.spend_concentration_pct >= 20 then 4 when con.spend_concentration_pct >= 10 then 3 when con.spend_concentration_pct >= 5 then 2 else 1 end
            + case when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.5 then 5 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.3 then 4 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.2 then 3 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.1 then 2 else 1 end
            + case when q.quality_score < 60 then 5 when q.quality_score < 70 then 4 when q.quality_score < 80 then 3 when q.quality_score < 90 then 2 else 1 end
        ) >= 9 then 'high'
        when (
            case when con.spend_concentration_pct >= 30 then 5 when con.spend_concentration_pct >= 20 then 4 when con.spend_concentration_pct >= 10 then 3 when con.spend_concentration_pct >= 5 then 2 else 1 end
            + case when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.5 then 5 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.3 then 4 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.2 then 3 when lt.avg_lead_time_variance_days >= lt.avg_lead_time_days * 0.1 then 2 else 1 end
            + case when q.quality_score < 60 then 5 when q.quality_score < 70 then 4 when q.quality_score < 80 then 3 when q.quality_score < 90 then 2 else 1 end
        ) >= 6 then 'medium'
        else 'low'
    end as overall_risk_level

from supplier_base as sb
left join supplier_total_spend as sts on sb.supplier_id = sts.supplier_id
left join concentration as con on sb.supplier_id = con.supplier_id
left join lead_times as lt on sb.supplier_id = lt.supplier_id
left join quality as q on sb.supplier_id = q.supplier_id
