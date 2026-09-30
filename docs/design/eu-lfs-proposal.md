# Eurostat research proposal: draft answers

*Bold text marks fields for the applicant to complete (yellow in the Word version).*

Access to EU Labour Force Survey scientific-use files. Draft prepared 12 September 2026, revised 25 September 2026 (2025 reference year; full variable list) for entry into the Eurostat microdata access portal, following the numbering of Research proposal application form v2.2. Yellow fields are for the applicant to complete; everything else is proposed text.

## 1. Research entity

| Field | Entry |
|---|---|
| 1.1 Research entity identification number | **[to fill: obtain from the World Bank DEC contact person]** |
| 1.2 Research entity name | World Bank - Development Economics Vice Presidency (DEC), Washington DC. Listed among Eurostat's recognised research entities (list of 30 July 2026); a second listing, "World Bank - Network of research units", also exists. |
| 1.3 Research entity contact person | **Haishan Fu** |
| Network contract | Not applicable: single research entity. |

## 2. Researchers who will have access to the data

### 2.1 Principal researcher

| Field | Entry |
|---|---|
| Name | Quy-Toan Do |
| Position | **Lead Economist** |
| Telephone | **+1 202 473 1248** |
| E-mail | **Qdo@worldbank.org** |
| Official full name of the research entity | International Bank for Reconstruction and Development (The World Bank), Development Economics Vice Presidency |
| English name | World Bank - Development Economics Vice Presidency (DEC) |
| Address | 1818 H Street NW, Washington, DC 20433, United States |
| Web address | https://www.worldbank.org/en/about/unit/unit-dec |

### 2.2 Data manager

Same as the principal researcher unless DEC designates a data manager to receive the encrypted files. Fill in only if different.

### 2.3 Individual researchers

| Field | Entry |
|---|---|
| Name | Gabriel Demombynes |
| Position | Manager, Human Capital Project |
| Telephone | +1-202-640-3889 |
| E-mail | gdemombynes@worldbankgroup.org |

## 3. Purpose of the research proposal

### 3.1 Title

Generative AI exposure and occupational employment dynamics in Europe and emerging economies: evidence from harmonised labour force surveys, 2021-2025

Published on Eurostat's website together with the dataset, entity name and starting year.

### 3.2 Description of the research project (maximum 2 pages)

Objective. The project asks whether the diffusion of artificial intelligence since late 2022 has changed the employment trajectory of occupations whose tasks are most exposed to it, and whether any change is concentrated among young and newly hired workers. It extends to Europe a cross-country panel that the researchers are building from national labor force surveys in fourteen emerging economies (Argentina, Bolivia, Brazil, Colombia, Mexico, Ecuador, Egypt, Georgia, India, Nigeria, Peru, the Philippines, South Africa, Uruguay), harmonised to a common schema based on the World Bank Global Labor Database dictionary with occupation coded to ISCO-08 and industry to ISIC Rev. 4. The EU-LFS is the only source that adds a large group of high-income economies with identical concepts, a common quarterly frequency and ISCO-08 occupation codes at three digits.

Background. Brynjolfsson, Chandar and Chen (2025) document, from United States payroll records, a relative fall in employment of workers aged 22 to 25 in AI-exposed occupations after 2022 with no fall for older workers, a pattern they attribute to adjustment at the hiring margin. Humlum and Vestergaard (2025) find no such effect in Danish administrative data. Fairlie and Wu (2026), using Current Population Survey microdata, find no rise in unemployment among recent college graduates in the summer of 2026 relative to earlier years, to older graduates or to young workers without degrees, so the United States evidence is itself unsettled. Evidence outside the United States and Denmark rests on job-posting data (World Development Report 2026, "The Promise of AI") or on single-country microdata (Aguirre and Meloni 2026 for Brazil; Ravanilla 2026 for Philippine business-process outsourcing). No study compares the age profile of employment in exposed occupations across a large set of countries on survey microdata, and none tests whether the result depends on national AI adoption, labor-market institutions or the size of the tradable services sector.

Research questions. (1) Did employment in high-exposure occupations grow more slowly than in low-exposure occupations after the fourth quarter of 2022, holding constant country, age-group and quarter effects? (2) Is any gap concentrated among workers aged 15 to 29 and among recent hires, in the current job for less than twelve months, as the hiring-margin hypothesis predicts? (3) Does the gap vary with national AI adoption, with the share of temporary and part-time employment, and between European and emerging economies? (4) Are the results robust to alternative exposure measures and to the level of occupational aggregation?

Data and design. The unit of analysis is the cell defined by country, calendar quarter, ISCO-08 occupation at three digits, five-year age group and sex, built from the quarterly EU-LFS scientific-use files for all countries from 2021 to the latest available reference year, with 2018 to 2020 as a pre-trend check. Occupation exposure comes from the ILO generative-AI occupational exposure index (Gmyrek, Berg and Bescond 2025), defined at the ISCO-08 unit group and aggregated to minor groups with employment weights; the Anthropic Economic Index usage measure, the Felten, Raj and Seamans index and the Eloundou et al. GPT exposure measure serve as alternatives. Outcomes per cell are weighted employment, the share of workers who started their current job within the previous twelve months (from YSTARTWK and MSTARTWK), the share on temporary contracts, usual and actual weekly hours, and the position of employees in the national distribution of monthly take-home pay (INCDECIL). The specification is an event study around the fourth quarter of 2022 with cell fixed effects and country by age group by quarter fixed effects, a triple-difference version interacting exposure with age, and a continuous-exposure version. Standard errors are clustered by country and occupation. The European estimates are compared with those from the fourteen emerging economies produced with the same code.

Why the EU-LFS. The design requires occupation at three digits, quarterly frequency, age detail sufficient to isolate labour-market entrants, and job tenure, harmonised across many countries. National public-use files do not provide this: Spain's public EPA file codes occupation at one digit, France's public file at two digits with age in six bands, Portugal has no public file, and Ireland's archive file is coded at the major group. The scientific-use file supplies ISCO at three digits, age in single years or five-year groups, the month and year the current job started, status in employment and contract type for the 27 member states plus Iceland, Norway, Switzerland and the United Kingdom, with the quarterly weights needed to reproduce Eurostat's published series.

Contracting. The project is the principal researcher's own research within the World Bank's Development Economics Vice Presidency. It is not commissioned by any other body and has no external funding contract.

Timetable. Delivery is expected in January 2027, after the December 2026 release that adds the 2025 reference year. Data preparation in the first six months after delivery; estimation and a working paper within twelve months; updates as further reference years are released within the access period.

### 3.3 Why the purpose cannot be fulfilled with publicly available data

Eurostat's published LFS tables give employment by occupation at the ISCO-08 major group and, in annual tables, at the sub-major group, cross-classified with broad age bands but never simultaneously with occupation at three digits, five-year age group, sex and quarter. The exposure of occupations to generative AI varies substantially within sub-major groups: in the ILO index, about half of the employment of legal, social and cultural professionals (ISCO 26), a third of science and engineering professionals (21) and four fifths of business and administration associate professionals (33) falls in the most exposed fifth of occupations, so one- and two-digit tables mix exposed and unexposed workers and attenuate any effect. Published tables also lack job tenure, the basis of the hiring-margin outcome, and cannot support cell-level fixed-effects estimation. The public-use LFS microdata files that Eurostat distributes are, by Eurostat's own description, unsuitable for inference about the population and code occupation and age too coarsely. The national statistical offices' open files were reviewed one by one (see 3.2) and do not carry three-digit occupation codes.

### 3.4 Duration of access requested

From **01/01/2027** to **31/12/2029** (three years; the maximum is five). The start date matches the expected delivery of the release that includes the 2025 reference year.

## 4. Datasets to be used

| Field | Entry |
|---|---|
| 4.1 Dataset | Labour Force Survey (LFS) |
| 4.2 Countries | All countries in the EU-LFS scientific-use file: the 27 EU member states (Belgium, Bulgaria, Czechia, Denmark, Germany, Estonia, Ireland, Greece, Spain, France, Croatia, Italy, Cyprus, Latvia, Lithuania, Luxembourg, Hungary, Malta, Netherlands, Austria, Poland, Portugal, Romania, Slovenia, Slovakia, Finland, Sweden), Iceland, Norway, Switzerland, and the United Kingdom (available to 2020Q3, for the pre-period). |
| 4.3 Type of confidential data | Scientific use files (partially confidentialised data delivered to researchers). No secure-use files, no safe-centre days, no access point. |

### 4.3 (continued) Variable groups, reference years and target population

Reference years: quarterly files 2018 to 2025. The 2025 reference year is expected in the yearly release of December 2026, and the request covers that release together with the earlier years, with delivery expected in January 2027; later releases within the access period are requested as they become available. The years 2018 to 2020 serve as a pre-trend check; the analysis window is 2021Q1 to 2025Q4. Yearly files for the same years for the structural variables listed below.

Target population: persons aged 15 to 74 in private households. The main analysis uses persons in employment (ILOSTAT = 1) aged 15 to 64; the whole working-age population is used for participation and unemployment checks against Eurostat's published series.

All variables in the LFS scientific-use file are requested, for the quarterly and the yearly files, as delivered under the anonymisation rules. The variables central to the analysis are (identifiers as in the 2021 legal acts):

- Technical: REFYEAR, QUARTER, REFWEEK, COUNTRY, REGION (NUTS 2), DEGURBA, COEFFQ, COEFFY, INTWAVE, HHNUM, HHSEQNUM.
- Person: SEX, AGE and AGE_GRP, CITIZENSHIP and COUNTRYB (regional groups), YEARESID, HATLEVEL and HATLEV1D, HATFIELD, HATYEAR.
- Labour market participation: ILOSTAT, EMPSTAT, WKSTAT, MAINSTAT, SEEKWORK, SEEKDUR, DURUNE, WANTWORK, AVAILBLE, LMSLACK, EDUC4WEEKS.
- Main job: ISCO4D as delivered at three digits (ISCO08_3D, ISCO08_2D, ISCO08_1D), NACE3D as delivered at section level (NACE2_1D, NACE2_S), STAPRO, FTPT, FTPTREAS, TEMP, TEMPDUR, TEMPREAS, TEMPAGCY, SIZEFIRM, SUPVISOR, HOMEWORK, NUMJOB, STAPRO2J, NACE2J2D.
- Tenure and work history: YSTARTWK, MSTARTWK, STARTIME, EXISTPR, YEARPR, MONTHPR, LEAVREAS, ISCOPR3D, NACEPR2D, STAPROPR, FINDMETH, LOOKOJ.
- Hours: HWUSUAL (usual weekly hours in the main job), HWACTUAL (hours actually worked in the reference week), CONTRHRS, EXTRAHRS, HWWISH, ABSREAS, HW2JOB.
- Income: INCDECIL, monthly take-home pay from the main job coded in national deciles, the only earnings variable in the scientific-use file, for the outcome on employees' position in the pay distribution.

### 4.4 How the dataset will be used

The quarterly files are the core input. They are aggregated to country by quarter by three-digit occupation by five-year age group by sex cells (employment using COEFFQ, shares of recent hires, temporary contracts and part-time work, usual hours), which form the estimation panel. The yearly files supply the structural variables (firm size, supervisory role, temporary-agency contract, field of education, take-home pay deciles) for heterogeneity analysis at the same cell level. Only the LFS is requested; it is not combined with any other Eurostat dataset. The cell panel is merged with occupation-level exposure indices and with country-level indicators from public sources (Eurostat aggregate tables, OECD, national AI-adoption surveys), never with other individual-level data.

### 4.5 Methods of statistical analysis

Descriptive employment indices by exposure tercile and age group; two-way and high-dimensional fixed-effects regressions on the cell panel (event study, difference in differences, triple difference, continuous treatment) estimated by weighted least squares with cluster-robust standard errors and a wild-cluster bootstrap where clusters are few; leave-one-country-out and synthetic-control robustness; sensitivity to the occupational aggregation level (two versus three digits) and to alternative exposure indices. Estimation in Python (statsmodels, linearmodels, pyfixest) and Stata.

## 5. Results of the statistical analysis

### 5.1 Expected scientific results

Estimates, with confidence intervals, of the change in employment, in the recent-hire share and in the temporary-contract share of high-exposure occupations relative to low-exposure occupations after 2022Q4, overall and by age group, for the European countries pooled and by country group, and a comparison with the same estimates for the fourteen emerging economies in the companion panel. The output consists of regression tables, event-study figures and aggregate cell-level indices that meet the publication thresholds. No individual-level derived dataset and no synthetic dataset will be produced or released.

### 5.2 Dissemination

A World Bank Policy Research Working Paper and submission to a peer-reviewed journal; presentations at World Bank seminars and academic conferences; a World Bank blog post; publication of the estimation code and of the aggregate, threshold-compliant cell estimates in the project's public GitHub repository. Publications will cite the EU-LFS by its DOI, carry Eurostat's standard disclaimer, and be reported through the Microdata Access Portal.

## 6. Safekeeping of confidential data for scientific purposes

### 6.1 Compliance with safekeeping requirements

Confirm each point for the World Bank DEC environment after checking with the DEC contact person and IT: **[to confirm]**

- Data stored on a server or stand-alone machine managed by World Bank IT.
- Access only from World Bank-managed clients with end-point security (encryption, malware protection, authentication, access controls).
- Access only from World Bank premises; no access to the files while working from home.
- Access restricted to the researchers named in the proposal.
- No export or copy to cloud systems, external AI or machine-learning platforms, external storage devices or mobile devices.
- Secure disposal of the data and of confidential intermediate results at project completion, with the destruction declaration.
- Clear separation of the DEC IT environment from the rest of the organisation, if the entity is registered as a department.

### 6.2 Anonymity of statistical units in published results

All results are aggregates over cells defined by country, quarter, three-digit occupation, five-year age group and sex, or regression coefficients estimated from such cells. Following Eurostat's Guidelines for publication for LFS scientific-use files, no figure based on three or fewer unweighted observations will be published; estimates below each country's reliability limit 'a' will be suppressed and those between limits 'a' and 'b' flagged as of limited reliability; no table at single-year age will be published; occupation will never be shown below the three-digit level delivered, nor region below NUTS 2. Cells under the threshold are dropped before estimation or merged into the parent two-digit occupation, and any released cell-level index carries its unweighted count so that suppression can be verified. Regression output reveals no individual record. The files, intermediate extracts and all copies are held only on the designated World Bank machine and destroyed at the end of the project.

## Notes for the applicant (not part of the submission)

- Procedure: entity recognition is already in place for DEC; the proposal is entered in the portal at https://ec.europa.eu/eurostat/web/microdata/access with an EU Login. Eurostat's estimate is about eight weeks, including a four-week consultation of the national statistical offices, each of which may withhold its country's data.
- Limits of the file that affect the design: economic activity is delivered at NACE section level only, so the IT and business-process-outsourcing industry block used in the emerging-economy panel cannot be reproduced; occupation is two-digit for Bulgaria and Slovenia and one-digit for Malta; age is in five-year groups for Czechia, Ireland, Malta, the Netherlands, Slovakia and Iceland; Germany is a 70 percent subsample with anonymisation weights; region is NUTS 1 for Germany, Austria and the United Kingdom and blanked for the Netherlands; single-year age tables may not be published.
- Section 6.1 shapes the workflow: the files may only be processed on World Bank-managed machines on Bank premises, with no cloud storage and no external AI tools. The panel code can run on such a machine, but the current setup on a personal Mac would not comply.
- Reference years: the current release (December 2025) stops at 2024; the application asks for 2018 to 2025 so that the December 2026 release, which adds the 2025 quarters, is delivered in January 2027 without an amendment. If Eurostat approves before that release, ask for the 2024 file immediately and the 2025 file on release; the proposal text covers both.
