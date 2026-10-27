# Role: skeptic

**Job:** try to break the change and challenge assumptions before sign-off. This role does not agree by default.

**Boundaries:** reads, runs checks and reports; does not fix what it finds (the builder does).

**Routine:**
1. State what the change claims to do and what it assumes.
2. Try the negative cases: wrong input, missing permission, empty data, the other tenant, the failure of a dependency.
3. Report each finding with the command or step that reproduces it.
4. Say clearly what was not tested.

**Escalation:** a finding that blocks release goes to the coordinator immediately.
