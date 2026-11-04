# Preregistration

Status: FROZEN for Study 1 (2026-10-29). Frozen by the tag `prereg-sweep-s0s2` on the commit that contains this file, before any call of `config/sweep_s0s2.json`. Any later change is reported as a deviation.

## Study 1: distance sweep, S0 vs S2 (`config/sweep_s0s2.json`)

### Question

Does the S2 reasoning scaffold move the distance at which Haiku 5.5 stops answering WALK on the v1 parking-meter item?

### Item and key

- Template, verbatim from the final v1 T6 prompt except for the distance: "My parking meter expires in 3 minutes. The meter machine is {d} meters away. There is no parking app available. You must choose one: should I walk or drive to extend my parking time?"
- Distances: 25, 50, 100, 150, 200, 250, 300, 350, 400, 500 m.
- Key: WALK at every distance. Driving vacates the spot the payment is for; arriving late on foot risks at most a fine. The human curve (`validation/`) is collected separately and does not change the key.

### Conditions and sample

- Model `claude-haiku-5-5`, effort `low`, through `claude -p` (fixed minimal system prompt, no tools, no MCP, no settings, no session, empty working directory). The reported model id is logged per call.
- S0 (no scaffold) and S2 (v1 text, verbatim, before the question). The answer instruction is always the last block.
- 20 calls per distance and condition: 400 calls. Trial order is shuffled with seed 20261029.
- The 20 probe calls already made (`runs/shades_t6_probe.jsonl`, `runs/sweep_step1.jsonl`) are exploratory and excluded.

### Outcome

`walk` = the forced final line is `ANSWER: WALK` (`ccb2/answer.py`, last line only). Format failures (missing or conflicting answer line) are excluded in the main analysis and counted as DRIVE in the sensitivity analysis.

### Analysis (`analysis/sweep.py`)

- **H1, primary.** S2 shifts the WALK curve. Test: Cochran-Mantel-Haenszel test of WALK vs DRIVE between S2 and S0, stratified by distance, two-sided, alpha 0.05, continuity-corrected. Strata where both conditions answer only WALK or only DRIVE carry no information and are dropped. Reported with the pooled odds ratio.
- **Tipping point, descriptive.** d50 per condition: the first distance where the WALK rate falls below 0.5, interpolated on log distance between the two neighbouring distances. Difference S2 minus S0 with a 95% percentile bootstrap CI (2,000 resamples within each cell).
- **Inference scope.** Repeated calls are independent draws from the model given a fixed prompt, so the test is valid for this wording. Generalisation to other wordings is a limit of the study and is not claimed.

### Power

Simulated in `analysis/sweep.py --sim` with a steep logistic curve (4 logit units per doubling of distance) and S0 d50 = 200 m: with 20 calls per cell, power 0.39 for a 25 m shift, 0.92 for 50 m, 1.00 for 100 m (with 10 calls: 0.18, 0.63, 1.00). The probes suggest a shift of about one distance step (50 m), hence 20 calls. A null result is read as: no shift of 50 m or more is likely; smaller shifts are not ruled out.

### Exclusions and errors

Calls that error after 3 attempts are rerun, never imputed. No call is dropped after it has been seen.

### Secondary, exploratory

A blind Opus judge codes each response. Its rubric is written and frozen before judging and includes, for DRIVE answers: ignores the spot, plans to take the spot back, treats a late arrival as impossible. These outcomes are exploratory.

## Study 2: placebo control (`config/sweep_placebo.json`)

Frozen by the tag `prereg-sweep-placebo` before any call of this config. Written after Study 1 results were known (S2 shifted the curve toward WALK, d50 +69 m).

### Question

Is the Study 1 shift caused by the content of S2 (means-ends analysis) or by adding any instruction block of similar length before the question?

### Conditions and sample

- Same item, distances, model, effort, runner and answer rule as Study 1.
- PLACEBO (66 words, formatting advice only, no reasoning content, prefix) and S0 rerun concurrently as the control, so both arms share the same time window.
- 20 calls per distance and condition: 400 calls, shuffled with seed 20261030.

### Analysis (`analysis/sweep.py`, same functions as Study 1)

- **H2, primary.** PLACEBO vs concurrent S0: CMH test stratified by distance, two-sided, alpha 0.05, with d50 difference and bootstrap CI.
- **Reading.** Placebo shift not significant and well below +69 m: the Study 1 effect is attributed to the content of S2. Placebo shift significant and similar in size to S2: the effect is a generic prompt-length or instruction effect. In between: reported as partial.
- **Secondary, descriptive.** S2 (Study 1) vs PLACEBO (Study 2), CMH; this comparison crosses two run windows and is labelled as such. Drift check: S0 Study 1 vs S0 Study 2, CMH; a significant drift is reported and weakens the cross-run comparison.

## Study 3: S4 and S5 (`config/sweep_s4s5.json`)

Frozen by the tag `prereg-sweep-s4s5` before any call of this config. Written after the results of Studies 1 and 2 and their judge coding were known.

### Question

Do the other two v1 scaffolds move the WALK/DRIVE curve as S2 does, and do they change how the responses treat the spot and the risk of arriving late?

### Conditions and sample

- Same item, distances, model, effort, runner and answer rule as Studies 1 and 2.
- S4 and S5 (verbatim from v1, prefix). 20 calls per distance and condition: 400 calls, shuffled with seed 20261031.
- No S0 is rerun. The control is the 400 S0 calls of Studies 1 and 2, pooled. This run happens in a later time window, so a drift of the model between runs cannot be ruled out; the S0 drift check of Study 2 covers only the two earlier runs.

### Analysis (`analysis/sweep_s4s5.py`)

- **H3, primary.** S4 vs pooled S0 and S5 vs pooled S0: CMH test stratified by distance, two-sided, Bonferroni alpha 0.025 per test, with d50 difference and bootstrap CI.
- **Secondary, descriptive.** S4 and S5 vs PLACEBO and vs S2, CMH, labelled as crossing run windows.
- **Reading.** A scaffold shifts the curve if its H3 test is significant. Its shift is attributed to content beyond the added instruction only if it is also significant against PLACEBO.

### Judge coding (exploratory)

- Same rubric, judge and blinding as the judge section below (`ccb2/judge.py` at the tag `judge-rubric-sweep`, unchanged), on the 400 new responses. Same descriptive questions, with S4 and S5 added.
- No Codex re-judging in this study (`--codex-share 0`), by decision of the author.

## Judge coding of Studies 1 and 2 (exploratory)

Frozen by the tag `judge-rubric-sweep` before any judgment of the 800 responses, written after the WALK/DRIVE results of both studies were known. Rubric and schema: `ccb2/judge.py` at that tag. Four smoke judgments made while writing the rubric are not kept.

- Judge: `claude-opus-5-5`, effort medium, via `claude -p` (no tools, no settings). It sees the bare question and the response, never the scaffold or the condition. Responses written under S2 may still reveal their condition by their structure; the judge is blind to the label only.
- Codex (`gpt-5.6-sol`) re-judges a random 20% (seed + 1) to check for same-family bias. Agreement is reported per field (Cohen's kappa).
- Fields added for the sweep: `spot_handling` (not_mentioned, reason_to_walk, plans_to_retake_spot, mentioned_but_dismissed), `lateness_framing` (not_discussed, late_is_impossible, late_is_tolerable_risk), `mentions_fine`, `suggests_running`.
- Questions, all descriptive with Wilson CIs, compared across S0, PLACEBO and S2: (1) among WALK answers, the share that give the spot as the reason (`spot_handling = reason_to_walk`); (2) among DRIVE answers, the split of `spot_handling`; (3) the share with `lateness_framing = late_is_impossible`, overall and among DRIVE. If S2 raises (1) above PLACEBO, its extra WALK answers come from noticing the spot; if not, they come from a more cautious time calculation.
- Before any claim in a paper, a human double-codes a stratified sample of 100 responses on `spot_handling` and `lateness_framing`; kappa below 0.7 with the judge sends the rubric back for revision.

## Earlier design (superseded, not run)

The paired-scenario design below was replaced by the distance sweep on 2026-10-29. It is kept for reference.


Freeze by tagging the commit (`v2-prereg`) after the pilot and the human key validation, and before the `core` run. Any later change is reported as a deviation.

### Hypotheses (core study, Haiku 5.5)

- **H1 (constraint-specific harm):** S2 lowers the WALK rate more on `keep_spot` than on `errand`. Test: the `scaffolded:inverse` term in `correct ~ scaffolded * inverse + high_effort`, logistic, cluster-robust SE by scenario, two-sided, alpha 0.05.
  - A negative coefficient supports the tunnel account.
  - A null with a main effect of `scaffolded` supports a general DRIVE bias.
  - A null with no main effect means the scaffold changes nothing.
- **H2 (effort):** the H1 interaction differs between low and high effort (`scaffolded:inverse:high_effort`). This test is exploratory in power and reported with its CI.

### Outcomes

- Primary: `correct` from the forced answer line. Format failures are excluded in the main analysis; in the sensitivity analysis they count as incorrect.
- Secondary (judge, after the kappa gate): `mentions_car_must_stay`, strict pass (WALK and mentions the constraint) on `keep_spot`, and the distribution of `primary_reason`.

### Sample

- 12 scenarios x 30 reps (or 24 x 15) x 2 variants x 2 scaffolds x 2 efforts = 2,880 calls, 360 per cell.
- Assumed effect for the power analysis (`analysis/power.py`): errand 0.90 to 0.85, keep_spot 0.60 to 0.30. Power at 350 per cell is about 0.80 for one effort level.
- Repetitions of the same prompt are not independent: the scenario cluster is the unit for inference.

### Exclusions

- Calls that error after 3 attempts are rerun, never imputed.
- A scenario is dropped before the core run, never after, if fewer than 70% of human raters agree with its key on any variant.

### Secondary tests (extensions)

All secondary tests are Holm-corrected within each extension: PLACEBO vs S2 on the H1 contrast, PRECOND vs S0 on `keep_spot`, prefix vs suffix, and Sonnet 5.5 and Codex replication of H1.
