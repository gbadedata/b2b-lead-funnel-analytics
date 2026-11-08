# Data quality log (generated)

Written for the person who owns the data. Each issue says what was found, why it matters and what would fix it. Severity: high changes a conclusion; medium limits an analysis; low is minor or already handled.

## DQ01 [high] Deal records cover the whole lead period

- **Affected:** 2,002 (25.0%)
- **Finding:** The first recorded deal is dated 05 Dec 2017, but leads start 14 Jun 2017. Leads first contacted before 2018 show 3.0% conversion against 13.0% after.
- **Why it matters:** Conversion for 2017 leads looks far lower than it was, which would distort any trend or channel comparison that includes them.
- **Fix:** Analyse only leads from January 2018, and confirm with the CRM owner when deal logging began.

## DQ02 [high] Every lead has a recorded source

- **Affected:** 1,159 (14.5%)
- **Finding:** 60 leads have a blank origin and 1,099 are marked 'unknown'. In the 2018 cohort these unattributed leads convert at 19.6% within 90 days, against 9.9% for attributed leads.
- **Why it matters:** The best-converting group has no source, so marketing spend cannot be tied to the leads that matter most.
- **Fix:** Make source a required field on the enquiry form and CRM, and audit how 'unknown' leads are created (for example manual or phone entries).

## DQ03 [high] Sales rep is recorded on every lead

- **Affected:** 7,158 (89.5%)
- **Finding:** SDR and sales rep IDs exist only on won deals; lost leads carry no rep.
- **Why it matters:** Rep conversion rates cannot be measured, only rep deal counts, which reward volume rather than skill.
- **Fix:** Record the assigned rep when a lead is first contacted, not when it is won.

## DQ04 [low] Won date is on or after first contact

- **Affected:** 1 (0.1%)
- **Finding:** 1 deal(s) are dated before the lead's first contact.
- **Why it matters:** Minor: these are treated as same-day wins and flagged.
- **Fix:** Check whether first contact is logged late for some leads.

## DQ05 [medium] Declared monthly revenue is usable

- **Affected:** 797 (94.7%)
- **Finding:** 797 of 842 deals (95%) record declared revenue as 0, which looks like 'not asked' rather than true zero; 2 record 1,000,000 or more (maximum 50,000,000).
- **Why it matters:** Deal value cannot be estimated from this field, so revenue analysis must use actual orders instead.
- **Fix:** Store 'not provided' as blank, not 0, and add a sense check on very large values.

## DQ06 [medium] Deal profile fields are filled in

- **Affected:** 756 (92.2%)
- **Finding:** Missing share: has_company 93%, has_gtin 92%, average_stock 92%, declared_product_catalog_size 92%.
- **Why it matters:** These fields cannot support segmentation or scoring.
- **Fix:** Either make them part of the closing checklist or drop them from the form.

## DQ07 [low] Behaviour profile has one clean value

- **Affected:** 193 (22.9%)
- **Finding:** 177 deals have no profile and 16 hold two values (for example 'cat, wolf').
- **Why it matters:** Profile-based reporting needs a rule for blanks and multiple values.
- **Fix:** Use a single-select field with an explicit 'not assessed' option.

## DQ08 [medium] Won sellers appear in order data

- **Affected:** 463 (55.0%)
- **Finding:** 463 of 842 won sellers have no order in the public order data.
- **Why it matters:** The public order file may not hold every order, so seller activation measured here is a lower bound.
- **Fix:** Use the full order table when this analysis runs on internal data.

## DQ09 [low] Order data is complete to its last date

- **Affected:** 21 (0.0%)
- **Finding:** Only 21 orders fall after 31 Aug 2018, against thousands per month before.
- **Why it matters:** Post-deal windows are cut at 31 August 2018 to avoid counting missing orders as no sales.
- **Fix:** Confirm the extract date before using the last weeks of any order file.

## DQ10 [low] Landing pages have enough traffic to compare

- **Affected:** 628 (10.5%)
- **Finding:** 328 of 407 landing pages had fewer than 10 leads in the 2018 cohort.
- **Why it matters:** Raw page conversion rates are noisy; pages are ranked on shrunk rates instead.
- **Fix:** Group pages by campaign or template so they can be compared.

## DQ11 [pass] Lead IDs are unique and every deal links to a lead

- **Affected:** 0 (0.0%)
- **Finding:** 8,000 unique leads; all 842 deals match a lead.
- **Why it matters:** None.
- **Fix:** None.
