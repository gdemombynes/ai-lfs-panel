# Linking persons across quarters (2026-09-17)

Most surveys in the panel are rotating panels. Since 2026-09-17 the
harmonised `pid` is stable across quarters wherever the source allows it, so
person-level transitions (entry into and exit from occupations, tenure
flows) can be built by joining adjacent quarters on `countrycode` and
`pid`, requiring `male` to agree and `age` to move by at most one year.

| Country | Source design | Key used | Adjacent-quarter match (persons found next quarter) | Sex and age agree | Longitudinal weights |
|---|---|---|---|---|---|
| Brazil | 5 interviews over 5 quarters | UPA + V1008 + V1014 + person order, visit number V1016 | 72 % | 97 % | none published by IBGE; users reweight from V1028 |
| Mexico | 5 interviews over 5 quarters | entry quarter (period minus n_ent - 1) + cd_a, ent, con, v_sel, tipo, n_hog, h_mud + n_ren | 73 % (all persons; about 90 % of those with n_ent < 5) | 100 % | none: the SDEM file carries fac_tri and fac_men only |
| South Africa | 4 quarters, a quarter of households rotates | UQNO + person number | 65 % | 96 % | none published by Stats SA |
| Argentina | two quarters in, two out, two in | CODUSU + NRO_HOGAR + COMPONENTE | 40 % | 91 % | none: PONDERA only |
| Uruguay | up to 6 consecutive months | ID + nper | 62 % | 96 % | none: monthly W only |
| Bolivia | rotating household panel | id_per_panel (INE) | 56 % | 100 % | none: fact_trim_act and fact_mes_act only |
| Peru | rotating panel, about 18 months | LLAVE_PANEL + C201 | 41 % (35 % a year later) | 99 % | none: FAC_T300 only |
| India, 2025Q2 on | 4 quarterly visits | household + person keys, visit number | 49 % | 100 % | none: mult only |
| Colombia | cross-section since 2022 | none | | | |
| Philippines | rotating design; public files scramble ids | none possible | | | |
| Ecuador, Georgia, Nigeria | rotating designs | rotation group kept; person link not built | | | |

Match rates are the share of persons in one quarter whose id appears in
the next quarter; they are below the design overlap because of attrition,
non-response and dwelling moves, and are lower for young and mobile
workers. No statistical office in the panel publishes longitudinal
weights, so transition rates need either the cross-sectional weight of the
base quarter with an attrition adjustment (inverse probability of being
re-observed, estimated on baseline sex, age, education, region and labour
status) or a comparison with the published gross-flow tables where they
exist (Brazil, Mexico and South Africa publish quarterly flow estimates).

Reuse checks: ids from quarters outside a panel's life do not link (Mexico
2022Q4 vs 2024Q1 zero matches once the entry quarter is in the key, against
58 % spurious matches without it; Bolivia 2022Q1 vs 2024Q1 zero matches;
Uruguay 64 of 28,000). Peru's LLAVE_PANEL persists a year or more by design.
Match rates and agreement above are measured on the harmonised files after
the 2026-09-17 change (`docs/compatibility.md` carries the duplicate-id
check; no country-quarter has duplicate ids except Uruguay's person-months,
which are counted on (pid, month)).
