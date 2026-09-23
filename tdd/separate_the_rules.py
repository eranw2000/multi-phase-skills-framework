"""Worked example of the "name the wrong implementations first" rule in SKILL.md.

Copy the shape, not the content. Write each candidate rule as a small function over a
fixture row, run every rule over the fixture, and refuse the fixture when any wrong rule
gives the same answer as the rule under test. It is a dozen lines and it answers in one
run the question that seven prose rules failed to make anyone ask.

The data here is a real incident: the fixture written to close
a review finding, which agreed with one wrong rule, and the fixture that replaced it,
which separates all five. Running it refuses exactly one of the two, and the exit status
asserts that, so the example cannot pass by refusing none or by refusing both.
"""

# The four candidate ranking rules, as they would really be implemented.
def three_bands(r):                      # the rule under test
    b = 0 if r["p"] + r["l"] else (1 if r["i"] else 2)
    return (b, -r["n"], r["name"])

def headcount_only(r):                   # no bands at all
    return (-r["n"], r["name"])

def two_bands(r):                        # interns lumped in with the rest
    return (0 if r["p"] + r["l"] else 1, -r["n"], r["name"])

def intern_is_legal(r):                  # an intern counts as legal
    return (0 if r["p"] + r["l"] + r["i"] else 1, -r["n"], r["name"])

def anyone_is_legal(r):                  # the mutation that actually SURVIVED on the day
    return (0 if r["p"] + r["l"] + r["n"] else 1, -r["n"], r["name"])

RULES = [("three bands (under test)", three_bands), ("headcount alone", headcount_only),
         ("two bands", two_bands), ("intern counted as legal", intern_is_legal),
         ("any group with anybody is legal", anyone_is_legal)]

def g(name, n, p=0, l=0, i=0):
    return {"name": name, "n": n, "p": p, "l": l, "i": i}

FIXTURES = {
  "the ORIGINAL, written to close the review finding":
      [g("Admin", 4), g("Interns", 1, i=1)],
  "the REPLACEMENT, after the procedure":
      [g("Admin", 4), g("Interns", 2, i=2), g("Sales", 1, p=1)],
}

bad = 0
for label, rows in FIXTURES.items():
    print(f"\n{label}")
    answers = {}
    for name, rule in RULES:
        order = [r["name"] for r in sorted(rows, key=rule)]
        answers[name] = tuple(order)
        print(f"   {name:28s} -> {', '.join(order)}")
    want = answers["three bands (under test)"]
    same = [n for n, a in answers.items() if n != "three bands (under test)" and a == want]
    if same:
        bad += 1
        print(f"   VACUOUS: agrees with {len(same)} wrong rule(s): {'; '.join(same)}")
    else:
        print("   SEPARATES all five. The test can only pass on the rule under test.")

print(f"\nfixtures the procedure would have REFUSED: {bad} of {len(FIXTURES)}")
raise SystemExit(0 if bad == 1 else 1)   # exactly one must fail, or this check is broken
