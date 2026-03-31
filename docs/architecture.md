# Architecture Notes

The system is intentionally infrastructure-first.

## Design Principles

- Keep data contracts explicit.
- Separate ingestion, research, pricing, ranking, and execution.
- Require inspectable workflow steps.
- Treat execution as optional and isolated.
- Prefer no-trade over low-quality conviction.

## Future Extension Points

- Replace static adapters with live HTTP-backed implementations.
- Route model calls by task class and cost budget.
- Introduce migrations once schema changes stabilize.
- Add tracing spans around each agent workflow stage.
