with

quality_scores as (

    select * from {{ ref('int_supplier_quality_score') }}

),

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

ranked as (

    select
        suppliers.supplier_id,
        suppliers.supplier_name,
        suppliers.is_active,
        quality_scores.total_quantity_received,
        quality_scores.total_quantity_rejected,
        quality_scores.defect_rate,
        quality_scores.quality_score,
        quality_scores.total_waste_quantity,
        quality_scores.total_waste_cost,
        quality_scores.total_receipts,
        quality_scores.rejected_receipts,
        rank() over (
            order by quality_scores.quality_score desc
        ) as quality_rank,
        case
            when quality_scores.quality_score >= 0.98 then 'excellent'
            when quality_scores.quality_score >= 0.95 then 'good'
            when quality_scores.quality_score >= 0.90 then 'acceptable'
            else 'poor'
        end as quality_tier

    from quality_scores

    inner join suppliers
        on quality_scores.supplier_id = suppliers.supplier_id

)

select * from ranked
