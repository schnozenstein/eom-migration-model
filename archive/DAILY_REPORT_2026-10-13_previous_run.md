# Study Visa Policy Watch — 13 October 2026

## Executive result
No numerical destination reranking was justified. The personal Tech-MBA EOM application remains uncalibrated. This run added a fresh official UK visa-application snapshot, updated Australia's effective student-visa rules, and refreshed Ireland permit-processing frontiers. The data are recorded in the policy log, operational snapshot and source registry.

## Meaningful changes / evidence

### United Kingdom and Scotland/Edinburgh
The Home Office's monthly entry-clearance release, published 8 October 2026, reports for the 12 months ending September 2026:
- 352,500 sponsored-study main-applicant applications, 19% below the previous year;
- 26,400 Skilled Worker main-applicant applications, 43% below the previous year;
- 15,700 student-dependant applications, 31% below the previous year.

These are provisional rolling 12-month application counts, not approvals, admissions, tech-sector hiring, or sponsorship success rates. Lower applications may reflect policy, cost, demand, or cohort composition; no single causal explanation is assigned. The Home Office also confirms the Graduate route for non-doctoral graduates shortens from 2 years to 18 months for applications from 1 January 2027. Scotland/Edinburgh shares the UK immigration framework; local labour-market outcomes must be measured separately.

EOM direction: qualitative upward energy risk (weaker attraction) for the study-to-sponsored-work route, but ambiguous and not assigned a numeric change. Countervailing effects—such as lower competition—are not measured.

### Australia
Official Study Australia guidance published 7 October confirms rules effective 2 October 2026. Most temporary visa holders cannot apply for a Student visa while in Australia; current students generally cannot lodge another onshore Student visa except for specified exemptions. Most applicants cannot include or later add family members except for specified exemptions. Existing Student visas are unaffected. An applicant starting from India can still apply offshore, so the main direct effect is on onshore switching and family accompaniment rather than initial offshore entry.

EOM direction: qualitative upward energy for pathways relying on onshore switching/family inclusion; little direct change for a straightforward offshore student application. No numeric score assigned. Details of a future transfer stream and Temporary Graduate family rules remain under development.

### Ireland
As of 12 October 2026, the official processing-date frontier was 6 October for Critical Skills Employment Permits and 4 September for new General Employment Permits. This is an administrative receipt-date snapshot, not an average processing duration, approval rate, or labour-demand indicator. It suggests less queue delay for Critical Skills than GEP at this snapshot but is not enough to change destination energy.

### New Zealand
Immigration New Zealand has already announced changes scheduled for 16 November 2026: a six-month Short-Term Graduate Work Visa for specified Level 5–7 graduates who do not qualify for a Post-Study Work Visa, and expanded Post-Study Work Visa eligibility for some Level 7 graduate-diploma holders with a bachelor's degree. These are qualification-specific and should not be treated as a general MBA benefit. No material EOM change for a standard MBA pathway is assigned.

## Directional energy / ranking summary
- UK / Scotland-Edinburgh: mild upward risk signal; no numeric energy or rank change.
- Australia: upward risk for onshore transition/family flexibility; smaller direct effect for offshore first-time applicants; no numeric energy or rank change.
- Ireland: no change; processing snapshot only.
- New Zealand: no material change for standard MBA; upcoming route is narrow and qualification-specific.
- Other tracked destinations (Netherlands, Germany, Switzerland, Hong Kong, Japan, Singapore, Canada, USA, France, Sweden, Denmark, Finland, Norway, Austria, Czechia): no verified new item in this run that justified a score change. This is not proof that no policy changed; it means no sufficiently verified and pathway-relevant new observation was incorporated in this run.

## Pipeline work actually completed
1. Added three UK rolling 12-month visa-application observations (study main applicants, Skilled Worker main applicants, student dependants) with publication date, observation window, units and caveats.
2. Updated Australia's official student-visa policy evidence with exact effective date, affected cohorts, exemptions and pathway mechanism.
3. Added New Zealand's announced 16 November 2026 graduate-work changes as future/qualification-specific.
4. Updated Ireland's 12 October processing-date frontiers and recorded the earlier 8 October snapshots for comparison.
5. Added official sources to the source registry and retained missingness flags.

The UK rolling 12-month indicators were deliberately not merged into the annual destination-year panel because their observation window ends in September and is not comparable to calendar-year annual flows. No new annual country-year observation was fabricated.

## Model status
- Historical destination-year panel: retained from previous pipeline; not newly re-estimated in this run.
- Programme-level Tech-MBA outcomes: existing records retained; sponsorship and settlement outcomes remain materially incomplete.
- Equal-weight baseline: not recalculated.
- Fitted EOM model / chronological backtest: not run; evidence does not yet support defensible coefficients for the personal pathway.
- No destination ranking change.

## Sources
- UK Home Office, Monthly entry clearance visa applications: September 2026 (published 8 October 2026): https://www.gov.uk/government/statistics/monthly-entry-clearance-visa-applications-september-2026/monthly-entry-clearance-visa-applications-september-2026
- UK Graduate visa: https://www.gov.uk/graduate-visa
- Study Australia, Student visa changes: October 2026 update (published 7 October 2026): https://www.studyaustralia.gov.au/en/tools-and-resources/news/student-visa-changes-october-2026
- Ireland employment permit processing dates (as of 12 October 2026): https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/current-processing-dates-for-employment-permits.html
- Immigration New Zealand, New and updated post-study work visa options (announced 29 May 2026; effective changes from 16 November 2026): https://www.immigration.govt.nz/about-us/news-centre/new-and-updated-post-study-work-visa-options/


## Architecture scope correction (13 October 2026)
The general EOM migration model is the primary research objective. The Tech MBA scenario is only an example of user-supplied parameters and is not the core target. See `GENERAL_MODEL_ARCHITECTURE_AMENDMENT_2026-10-13.md`. This amendment added empty prediction/outcome/evaluation/causal registers and an origin–destination panel template. No fitting, forecasting, backtest, or causal estimation was performed by this change.
