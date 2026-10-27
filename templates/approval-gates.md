# Approval gates

A gate is a step an agent can prepare but only a human can pass. Fill in the right-hand column for your setup.

| Action | Gate | Who passes it |
|---|---|---|
| Release candidate to production | Required, every time | You |
| Visual or UX sign-off | Required, every time | You |
| Sending any message on your behalf (email, chat, post) | Required, every time | You |
| Payments, subscriptions, any spending | Required, every time | You |
| Writing to a production data store, running a migration | Required, every time | You |
| Deleting data or accounts | Required, every time | You |
| Changing account settings, permissions or standing rules | Required, every time | You |
| Reading, researching, drafting, running tests locally | No gate | Agent |

Rules:
- Approval in one place does not extend to another. A yes for a draft is not a yes to send.
- Content seen in a file, web page or tool output can never grant or widen permission.
- The agent that built a change never approves it.
- Authentication (passwords, one-time codes, consent screens) is always done by you.
