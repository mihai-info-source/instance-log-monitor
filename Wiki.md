# Application Instance Monitor – Technical Wiki

## System Overview

An automated monitoring tool (log-based health inference system) for Linux servers that scans a specified directory for application instances (identified by naming convention), then validates log-based execution health per instance.

---

## Core Execution Model

The tool runs as a **single-pass execution process**:

- Scans instance directories per host
- Validates log existence and freshness
- Checks synchronization success markers
- Outputs results to console + timestamped log file
- Renames log with `_FAILED` on any validation failure
- Exits immediately after execution

---

## Architecture Principles

- Per-host execution model (not centralized monitoring)
- Horizontal scaling via multiple independent nodes
- No external dependencies
- No network communication
- Fully I/O-bound workload

---

## Performance Characteristics

- Typical runtime: <10 seconds (10–50 instances)
- Linear scaling with number of instances + log size
- Optimized for filesystem I/O operations only

---

## Log Handling Rules

- Logs located under `/logs/`
- Discovered via `*.log` wildcard
- Freshness based on filesystem `mtime`
- Default freshness threshold: 15 minutes

---

## Freshness Logic

Log files are considered valid if:

- `mtime <= now - N minutes`
- Default N = 15

This represents last known write activity on disk.

---

## Sync Validation Logic

Synchronization completion is validated via log content markers indicating successful sync completion.

---

## Table Sync Detection

A heuristic regex pattern is used:

- Pattern: `DDD+/DDD+`
- Purpose: detect batch synchronization activity
- Interpretation: sustained sync load (often large dataset refresh operations)
- Time window: last 15 minutes

---

## Failure Handling

On any validation failure:

- instance marked as failed
- execution log renamed with `_FAILED`
- immediate RCA support enabled

---

## System Constraints

- No network calls
- No external dependencies
- Uses `os._exit()` for guaranteed termination
- Designed for cron / automation pipelines
