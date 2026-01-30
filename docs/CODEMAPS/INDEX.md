# Codemaps Index

Last Updated: 2026-01-30

This directory contains architectural documentation for the Crypto DCA Trading Bot. Each codemap covers a specific area of the system and is generated from the actual codebase.

## Available Codemaps

| Codemap | Scope | Key Contents |
|---------|-------|-------------|
| [architecture.md](./architecture.md) | High-level overview | Repository structure, component dependency graph, data flow, validation pipeline, security architecture, design principles |
| [backend.md](./backend.md) | Module detail | Strategy class methods and parameters, indicator functions, risk manager API, script functions and data classes, test coverage mapping |
| [data.md](./data.md) | Configuration and storage | Config profiles and schema, trading pairs, historical data, database tables, frozen dataclass inventory, environment variables, evaluation criteria |

## Quick Navigation

- To understand the overall architecture and data flow: Start with [architecture.md](./architecture.md)
- To look up specific function signatures or class APIs: See [backend.md](./backend.md)
- To understand configuration options or database structure: See [data.md](./data.md)

## Project Summary

- Language: Python 3.11+
- Framework: Freqtrade 2024.x
- Strategy: DCA (Dollar Cost Averaging) with RSI-based entry
- Exchange: Binance Japan (JPY pairs)
- Current Phase: Phase 5 (Dry Run, 2026-01-30 to 2026-02-13)
- Total codebase: 28 source files, 6,088 lines (excluding docs)
- Test coverage target: 80%+

## Related Documentation

- [/docs/CONTRIB.md](../CONTRIB.md) -- Development workflow and setup
- [/docs/RUNBOOK.md](../RUNBOOK.md) -- Operational runbook
- [/docs/phase5-dryrun-operation.md](../phase5-dryrun-operation.md) -- Current phase operation manual
