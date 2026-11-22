# Safety

An agent with a mouse, a keyboard and a signed-in browser can do most things its owner can, including the wrong ones. The rules below are code that sits between the model and the tools. They are not instructions in a prompt, and the agent cannot edit them.

| Guardrail | What it does |
|---|---|
| Control grant | The first time it needs the mouse, keyboard or browser it asks out loud. The yes lasts ten minutes by default. |
| Kill switch | Ctrl+Alt+K stops anything in progress and revokes control. |
| Protected list | Banking, payment, crypto, brokerage and password-manager sites, and windows titled like them, are refused. It will not open, look at or click in them. |
| Secrets filter | Password fields are refused. Text that looks like a card number, a US SSN or a Canadian SIN is never typed. |
| Confirmation | Clicks on buttons like Buy, Send, Delete, Submit and Confirm, risky key combinations, shell commands, email drafts and calendar events need a yes first. No confirmation channel means no. |
| Injection screen | Text from web pages, search results, emails and files is checked for wording aimed at an assistant ("ignore your instructions", fake system messages, "the user already approved"). When it matches, the model receives the content with a warning in front, does not act on it, and tells me. |
| Loop guard | A task going round the same two or three steps with the same results is nudged on the third lap and stopped on the fourth. |
| Audit log | Every control action is appended to a log file. |
| Not built at all | There is no tool that sends email and no tool that deletes files. Memory refuses passwords and account numbers. |

## Unattended work

The job-application autopilot and scheduled agents cannot ask me, so they run on a fixed click policy. They may press the buttons an application needs (next, continue, upload, submit application) and nothing that spends money, deletes, or posts publicly. Each decision, approved or declined, is written to the audit log.

## Read the code

- [`samples/safety.py`](../samples/safety.py): kill switch, control grant, protected list, secrets filter, the confirmation policy for unattended agents, audit log.
- [`samples/guard.py`](../samples/guard.py): the injection screen and the loop guard.

## What this does not solve

The injection screen is a pattern check, so it can be evaded and it can raise false alarms. I treat it as one layer. The layers that do not depend on recognising an attack are the ones that matter most: blocked sites, confirmations that fail closed, and the kill switch.
