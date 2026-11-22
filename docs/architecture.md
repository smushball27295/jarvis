# Architecture

Jarvis is one Windows app with three layers: a voice front end, a model tool loop in the middle, and a registry of tools at the back. A full-screen display shows state, tool calls and results.

## The path of one request

| Step | What happens |
|---|---|
| Wake | "Hey Jarvis" is detected on the laptop by openWakeWord. Nothing leaves the machine until then. |
| Hear | Speech-to-text with Whisper, also local. Words it got wrong before are passed back as hints. |
| Shortcut | The time, job status, volume, fullscreen and spend are answered with no model call at all. |
| Route | Short everyday requests go to a small model. A turn moves up to the main model the moment it reaches for a heavy tool. |
| Act | One tool-use loop. The tool list, instructions and conversation are cached, so each step of a long task re-reads them at the cache price. 30 tool definitions are sent per request, out of 94. |
| Check | Every tool that clicks, types or sends goes through the safety layer first. See [safety](safety.md). |
| Reply | Voice starts on the first sentence. The screen shows what was done. |
| Learn | After the conversation a small model reviews it and writes lessons for next time. See [learning](learning.md). |

## Tools

Tools are plain Python functions registered with a name, a description and a JSON schema. Groups: browser (its own Chromium window through Playwright), desktop (screen capture, mouse, keyboard), files and documents, web and news search, email drafts and calendar, memory, usage, scheduled agents, the job-application autopilot, phone (Telegram), and a hand-off to a coding agent for building or changing software.

Sending the model all 94 definitions on every request was the largest single cost. A small selector now picks the groups a request can plausibly need and sends about 30.

## Agents for bigger jobs

For a job with several parts, Jarvis sets up a temporary organisation: a director that plans, managers that own a part, and associates that do one thing. Each agent gets only the permissions its task needs (for example, "may submit forms" but not "may send messages"). Money, deletion, shell commands and code changes are never delegated to an unattended agent.

## Staying up

A watchdog restarts the app if it stops, a self-test runs 380+ checks without calling a model, and a loop guard stops a task that keeps going round the same steps with the same results (a nudge on the third lap, a stop on the fourth).

## Changing its own code

Requests like "add a tool that reads my calendar for next week" go to a separate coding brain that can only touch the app's own folder. The change is backed up first. It is kept only if the code compiles, the program still starts and every safety rule is still in place. Otherwise the backup is restored. The safety files themselves are read-only to this process.
