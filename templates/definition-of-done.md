# Definition of done

A task is done when each line below is true **and** you can show the output. Completion is tied to checks that give the same answer every time, not to the agent's opinion.

- [ ] The change does what the request said (state it in one sentence).
- [ ] The automated tests pass. Command: `<your test command>`. Output pasted, with the count.
- [ ] The new behaviour has a test that was first shown failing against the old behaviour.
- [ ] Negative cases were tried (bad input, missing permission, dependency down).
- [ ] Lint and type checks pass. Command: `<your check command>`.
- [ ] Nothing outside the stated scope changed (`git diff --stat` shown).
- [ ] Anything not tested is listed under 'Not tested'.
- [ ] A gate that needs a human (release, visual, outward action) is marked **waiting**, not passed.

Report 'done' only after the boxes are ticked with evidence. A box without output stays unticked.
