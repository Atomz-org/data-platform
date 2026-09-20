-- A catalog entry with no live feed is priced from indicative_prices. One with
-- neither is a commodity nobody can quote, in every sister at once.
select c.commodity_id
from {{ ref('commodities') }} as c
left join {{ ref('indicative_prices') }} as i on i.commodity_id = c.commodity_id
where c.yahoo_symbol is null
group by c.commodity_id
having count(i.commodity_id) = 0
