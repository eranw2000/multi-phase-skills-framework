# Writing a non-functional requirement

An NFR like "the system must be fast and secure" cannot be tested. Turn each one into
an objective with these parts:

1. **Who and when**: the user or system and the situation ("a signed-in teacher opening a
   class report during the morning peak").
2. **What happens to it**: the load, input or event ("300 reports opened in 5 minutes", "the
   payment provider times out").
3. **Where and at what scale**: the environment and the size of data it runs on.
4. **What must stay true**: the expected response or rule ("no order is charged twice").
5. **The number or rule that decides pass or fail** ("95% open within 2 seconds").
6. **How it is observed**: the test, the log, the metric or the person who checks it.
7. **What is allowed to degrade, and how it recovers** ("a slower report is acceptable; a
   lost one is not; it recovers without a manual step").

Example: "NFR-PERF-1: For signed-in teachers opening a class report during the morning peak
(300 opens in 5 minutes, production-size data), 95% of reports open within 2 seconds, none
fails, and a single slow database query does not need a restart to recover. Observed by
the load test in CI and the p95 metric on the dashboard."

**Never invent the number.** If the user does not know it, write the NFR with the number
left open and add an Open Question that names who decides it and what would measure it.
A made-up threshold reads as agreed and is the first thing a later review anchors to.

Check these quality areas, and keep only the ones that matter for this product:
performance, reliability, compatibility, usability, accessibility, security, privacy,
maintainability, data quality, operability (can someone see what is wrong and recover it),
and portability (install, migrate, upgrade, roll back).
