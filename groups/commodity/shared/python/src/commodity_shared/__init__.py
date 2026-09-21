"""commodity group — what every sister shares and no sister owns.

Infrastructure, not business logic: the conformed catalog and market registry
(read from the group's dbt seeds, so Python and SQL cannot disagree), the
market-data connectors, and the reader a roll-up uses to see its sisters. A
market's own facts — duty, local units, exchange contracts — never live here.

Found by path, like a sister's own package: `pf.runtime.paths.import_paths`
puts `groups/<group>/shared/python/src` next to `<project>/src`.
"""
