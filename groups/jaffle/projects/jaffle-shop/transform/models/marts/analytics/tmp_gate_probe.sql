-- Throwaway: proves the impact gate lets an added model through.
-- A model that does not exist on the base branch has no downstream consumers
-- there, so it has no blast radius. Delete with the verification PR.
select 1 as probe
