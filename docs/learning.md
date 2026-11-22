# Learning

Jarvis improves by remembering. The model itself is not retrained.

After every conversation it reviews what was said and how each tool call went, in one call to a small model. The review is capped at 25 cents a day. It can write four kinds of note:

| Note | What it is | How it is used |
|---|---|---|
| Lesson | One sentence, written when I correct it or when its first approach fails and another works. | Added to its instructions on every turn. |
| Playbook | How a multi-step task was done when it worked. | The matching playbook is put in front of it when a similar request comes in. |
| Vocabulary | Names and words the speech recogniser got wrong. | Handed back to the recogniser as hints. |
| Code idea | A change to its own code that would have prevented a failure. | A proposal only. Making the change takes my yes. |

## Rules

- A lesson may only come from me or from its own experience. It may never come from a web page, an email or a file, because that would let outside text rewrite the agent.
- A lesson cannot change an approval or a safety rule.
- "What have you learned?" lists everything. "Forget that" removes an item.
