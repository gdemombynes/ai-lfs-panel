# Candidate countries (reviewed 2026-09-07)

What the design needs from a survey: quarterly (or monthly) microdata with
ISCO-08-compatible occupation at 3 digits or better, a window that reaches
back to 2021 or 2022 and forward to 2025, and enough sample for
occupation x age x sex cells (roughly 40,000 employed persons a quarter for
3-digit cells; smaller surveys work at 2 digits, as Argentina and Mexico do).
Checks done for each entry: catalogue reachable, latest release, access
rule, occupation coding.

## In the panel

Brazil, Mexico, Colombia, Argentina (urban), Ecuador, Peru, South Africa,
Georgia, Philippines, Nigeria (patchy), India.

## Tier 1: public or registration-only microdata, quarterly, scriptable now

| Country | Survey, source | Frequency and window | Occupation | Access | Sample | Notes |
|---|---|---|---|---|---|---|
| Uruguay | ECH, INE ANDA catalogue (ids 767 = 2024, 775/779 = 2025) | monthly panel since 2021 (implantation + follow-up files), semester releases; 2025 S2 out | CIUO-08, 4 digits (confirm on download) | registration, public-use terms | about 40,000 households a year | small country, but clean 4-digit coding and timely; clerical-heavy labour market |
| Costa Rica | ECE, INEC PAD/NADA (id 331 = 2024, 369 = 2025) | quarterly, one bundle per year, 2010-2025 | COCR-2011 (ISCO-08 based), 4 digits | registration | about 6,000 households a quarter (2-digit cells) | BPO exporter; INEC re-based the series in 2022-2023 (check the break) |
| Bolivia | ECE, INE ANDA (id 170 = 2025 Q2, 254 = 2025 Q3) | quarterly, 2022Q2-2025Q3 online | COB-2009 (ISCO-08 based), 4 digits | registration, public-use files | about 9,000 households a quarter (2-digit cells) | urban plus rural; weights by quarter |
| Palestine (West Bank) | LFS, PCBS microdata catalogue (ids 738-742 = 2024Q3-2025Q2) | quarterly, every quarter since 1995 | ISCO-08, 4 digits | licensed terms, online request | about 4,300 households a quarter (2-digit cells) | Gaza not surveyed since late 2023; West Bank only, a war-time series |
| Mongolia | LFS, NSO NADA (web.nso.mn) | quarterly, 2023 file in the catalogue | ISCO-08, 4 digits (GLD uses it at 4) | registration | about 12,000 households a year | to confirm quarter identifiers and 2024-2025 availability |

## Tier 2: request or licence, quarterly, good coding

| Country | Survey, source | Frequency and window | Occupation | How to get it |
|---|---|---|---|---|
| Dominican Republic | ENCFT, Central Bank | quarterly since 2014, 2026Q1 out | CIUO-08, 4 digits | email request to the Central Bank's free-access-to-information office; an R package (encftr) documents the files |
| Egypt | LFS, CAPMAS via ERF harmonized files (2021-2024) | quarterly rounds inside annual files; 2025 expected late 2026 | ISCO-08, 4 digits | ERF portal registration and per-dataset request; daily release watch already scheduled |
| Rwanda | LFS, NISR microdata catalogue (id 114 = 2024, 125 = 2025) | rounds in Feb/May/Aug/Nov since 2019; 2025 file created April 2026 | ISCO-08, 4 digits | registration under NISR's microdata release policy |
| Ghana | AHIES, GSS microdata (id 128) | quarterly Jan 2022-Dec 2024 | ISCO-08 (digits to check) | GSS licence; current version marked "office use only" |
| Türkiye | HLFS, TurkStat | quarterly | ISCO-08, 4 digits | formal microdata request to TurkStat |
| Thailand | LFS, NSO | quarterly | ISCO-08, 4 digits | request to NSO (data service) |
| Vietnam | LFS, GSO | quarterly | VSCO 2020 (ISCO-08 based), 4 digits | request to GSO |
| Sri Lanka | QLFS, DCS | quarterly | ISCO-08, 4 digits | request to DCS |
| Indonesia | Sakernas, BPS Silastik | February and August rounds | KBJI 2014 (ISCO-08 based), 4 digits | purchase through Silastik |
| Malaysia | LFS, DOSM | monthly and quarterly | MASCO 2013 (ISCO-08 based) | request to DOSM |
| Jordan | EUS, DOS | quarterly | ISCO-08 | request to DOS or ERF harmonized files (older years) |
| Serbia, North Macedonia, Albania, Armenia | LFS | quarterly | ISCO-08, 3-4 digits | national office requests; Armenia posts annual public files |

Rejected for coding depth: Chile ENE (public file carries occupation at the
major group; 4-digit CIUO-08.CL only by request to INE) and Paraguay EPHC
(public file at 1 digit). Not available at quarterly frequency: Kenya,
Tanzania (ILFS 2020/21 only), Uganda (annual), Pakistan (biennial),
Bangladesh (QLFS from 2022 but microdata restricted), Morocco and Tunisia
(quarterly surveys, microdata not released).

## Tier 3: high-income anchors

Useful as comparators for the Canaries-style result rather than as part of
the developing-country pool.

| Country | Survey, source | Frequency | Occupation | Access |
|---|---|---|---|---|
| United States | CPS via IPUMS | monthly | SOC 2018 (BLS SOC-ISCO crosswalk to 3-4 digits) | open, registration |
| Spain | EPA, INE | quarterly | CNO-11 at 3 digits (ISCO-08 based) | open download |
| Italy | RCFL, ISTAT microdata files | quarterly | CP2021 (ISCO-08 based) | open with registration |
| France | Enquete Emploi, INSEE | quarterly | PCS 2020 (crosswalk to ISCO) | open with registration |
| United Kingdom | LFS, UK Data Service (end-user licence) | quarterly | SOC 2020 (official crosswalk to ISCO-08 4 digits) | registration |
| Canada | LFS PUMF, Statistics Canada | monthly | NOC 2021 (crosswalk to ISCO) | open |
| Korea | EAPS, MDIS | monthly | KSCO (ISCO-08 based) | registration |
| EU | EU-LFS scientific-use files, Eurostat | quarterly, 27+ countries | ISCO-08, 3 digits | research application |
| Israel | LFS public-use file, CBS | monthly | ISCO-08 | registration |

## Suggested order

1. Uruguay, Costa Rica, Bolivia, Palestine: public or registration-only,
   quarterly, ISCO-08 at 4 digits, scriptable with the Georgia/Ecuador
   patterns (annual bundles with quarter identifiers, SPSS or Stata). Small
   samples, so 2-digit cells like Argentina.
2. Mongolia and the Dominican Republic once availability is confirmed.
3. Rwanda and Egypt after the registrations the user holds or starts.
4. Spain and the United States as open high-income anchors.
5. Türkiye, Thailand, Vietnam, Sri Lanka, Indonesia by formal request; each
   is a large, clerical- or services-rich labour market and worth the
   paperwork.
