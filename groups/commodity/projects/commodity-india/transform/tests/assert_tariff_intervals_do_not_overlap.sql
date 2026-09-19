-- Two tariff rows for one commodity covering the same day would double the
-- landed-price rows for that day. Returns every overlapping pair.
select a.tariff_id, b.tariff_id as overlapping_tariff_id
from {{ ref('india_import_duties') }} as a
inner join {{ ref('india_import_duties') }} as b
    on a.commodity_id = b.commodity_id
    and a.tariff_id < b.tariff_id
    and a.valid_from <= coalesce(b.valid_to, cast('9999-12-31' as date))
    and b.valid_from <= coalesce(a.valid_to, cast('9999-12-31' as date))
