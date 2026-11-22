# Cost

For an agent product, the cost of one finished task is the unit economics. If it cannot be measured, the product cannot be priced.

## The ledger

Every model call is recorded with what it was for (voice, autopilot, each agent), the model, the tokens including cache writes and reads, the cost and the latency. Asking "how much have I spent?" shows today, this month, the projection, spend by feature and what caching saved. Background work stops for the day at a budget (five dollars by default).

## The benchmark

A script replays three recorded sessions (a voice session, one job application and a stuck task) and prints the cost with the original request style and the current one. It calls no model and needs no API key, so the numbers are reproducible.

| One automated job application | Modelled cost |
|---|---|
| Original request style | about $1.60 |
| Current | about $0.13 |

## What changed between the two

1. **Prompt caching.** The tool list, the instructions and the growing conversation are cached, so each step of a long task re-reads them at the cache price instead of the full price.
2. **Fewer tool definitions per request.** 30 instead of 94. A selector sends only the groups a request can plausibly need.
3. **Routing.** Short everyday requests go to a small model. A turn moves up to the main model only when it reaches for a heavy tool.
4. **No model at all for some requests.** The time, volume, job status and spend are answered locally.
5. **Stopping waste.** A call that keeps returning the same result is stopped after five tries, and a short cycle of calls is stopped on the fourth lap.

## Where it started

The first audit of the logs found about 430 tool calls for one submitted application, and sessions that ended on an empty API balance. That audit is why the ledger, the benchmark and the budget exist.
