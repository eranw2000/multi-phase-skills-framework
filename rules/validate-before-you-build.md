# Validate before you build, when building is the expensive part

Every plan rests on some assumption about how a system behaves. When that assumption can only be settled by seeing it run, and the real stack is slow or costly to try things in, build a small throwaway proof of concept first.

A proof of concept is warranted when both hold:

1. **The question needs running code to answer.** Reading docs or code will not settle it.
2. **The target is slow or expensive to iterate in.** For example: a private data feed, a server you cannot reach from your machine, a deploy-to-test loop, or an environment that will not run locally.

**Decide during planning and write the decision down either way**, including "no proof of concept, because X". A missing line reads as "nobody thought about it".

When you build one, write down two things before you trust its answer:

- **What it could not validate.** A proof of concept on a laptop says nothing about the production network, the real data volume or the real permissions. Name those parts so nobody reads the result as covering them.
- **What decides pass or fail, frozen before it runs.** Say what the expected result is and where that expectation comes from, and do not change it after you see the output.

Ask the question once while gating the plan (`/plan-gate` in this pack), not after the build has started.
