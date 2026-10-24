# Backlog

Planned work, grouped into small projects. Ticked items are done; `LOG.md` has the dates.

## ppt-transition (paused)

- [x] Add the Morph skill and its engine, with end-to-end tests on generated decks
- [ ] Split `morph.py` into a package (package, matching, ghosts, CLI) with the skill's extract step still working (too large for one day: the skill embeds `morph.py` as one block, so plan the extract step first)
- [x] `--dry-run` summary as a table of slide changes: morph, glide, fade counts and weak matches
- [x] Test the matching score on hand-built pairs: same text, moved shape, same image, footer
- [x] `check` command: re-open a morphed deck and list slides whose transition or `!!` names are broken
- [x] Build the skill's web page from `SKILL.md`, the way ppt-designer does

## ppt-designer (in progress)

- [x] Add the skill and a tested deck reader for PDF decks
- [x] Flag slides that break the skill's own limits: type under 8pt, more than 450 words
- [x] `--json` and `--csv` output so results can be compared across decks
- [x] Read `.pptx` directly with python-pptx, without converting to PDF first
- [x] List topic-only titles (no verb and no number)
- [x] Draft a deck card from the measurements, using the template in the skill
- [x] Rubric scorer: enter 1, 3 or 5 on the five criteria and get a report with the weakest first
- [x] Build the skill's web page from `SKILL.md`
- [ ] Serve the skill's page with GitHub Pages
- [x] Resolve `.pptx` type sizes inherited from the slide layout and master
- [x] Add `titles.py` results to `deck_reader.py --format json` so one run gives the full check
- [ ] `deck_card.py --render` to save slide images beside the card for filling in the layout fields

## Product analytics

- [ ] Cohort retention table from an events CSV
- [ ] Funnel conversion with step-to-step drop-off
- [ ] A/B test significance for two proportions
- [ ] Sample-size calculator for an A/B test
- [ ] RICE and ICE scoring from a CSV of ideas
- [ ] North-star metric tree with rollups
- [ ] SQL for common product questions: DAU, WAU, MAU, stickiness, retention

## Fintech

- [ ] EMI and amortisation schedule
- [ ] XIRR for irregular cash flows
- [ ] UPI VPA and IFSC validators
- [ ] Rule-based spend categoriser for a bank-statement CSV
- [ ] Ledger reconciliation between two CSVs

## Procurement and operations

- [ ] Lead-time variance: planned against actual delivery, by vendor
- [ ] Payables ageing from a list of purchase orders
- [ ] Vendor scorecard: on-time rate, average delay, share of spend

## Growth and unit economics

- [ ] Revenue model: traffic x conversion x order value, by channel
- [ ] CAC, LTV and payback calculator
- [ ] Break-even and contribution margin calculator
- [ ] Price elasticity from two price points

## Statistics

- [ ] Confidence interval for a mean and for a proportion
- [ ] One-sample and two-sample t-tests from scratch
- [ ] Simple linear regression from scratch, with R-squared

## Fitness and nutrition

- [ ] TDEE and macro split calculator
- [ ] Progressive overload planner
