# Analysis plans and their timing

Each study had a written analysis plan (hypothesis, sample, test, reading rule) committed in the private development repository and marked with a git tag before its first model call. The plans were not deposited in a public registry. This folder holds a copy of the plan file as it stood at each tag, and the record below is the only evidence of timing.

| Study | Tag | Tagged commit | Push recorded by GitHub (UTC) | First model call (UTC) |
|---|---|---|---|---|
| 1. S2 vs S0 | `prereg-sweep-s0s2` | `c5e78da` | 2026-10-29 11:15:33 | 2026-10-29 11:15:58 |
| 2. Placebo vs S0 | `prereg-sweep-placebo` | `5c73cf4` | 2026-10-29 15:12:31 | 2026-10-29 15:12:44 |
| Judge rubric | `judge-rubric-sweep` | `2940d4d` | 2026-10-29 15:57:38 | after the push |
| 3. S4, S5 | `prereg-sweep-s4s5` | `65aa612` | 2026-10-31 14:59:40 | 2026-10-31 14:59:53 |
| 4. S1, S3 | `prereg-sweep-s1s3` | `7081305` | 2026-11-03 20:30:14 | 2026-11-03 20:30:25 |

Push times come from the GitHub repository activity log of the private repository. First call times are the earliest `ts` field in each file of `runs/`. The full history of the private repository is available on request.

## Reading these files

- `prereg-sweep-*.md` and `judge-rubric-sweep.md`: the plan file at each tag. `judge-rubric-sweep_judge.py`: the judge prompt and rubric at that tag.
- `PLANS_FINAL.md`: the plan file in its last state.
- The plan file was drafted by Claude (the AI assistant) and carries over sections from an earlier design based on several scenarios. That earlier design, the human answer curve and the human double coding it mentions were never run. The paper reports only the distance sweep.
- The plans for Studies 2 to 4 were written after the results of the earlier studies were known.
