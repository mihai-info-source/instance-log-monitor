# Application Instance Monitor

**Author:** Mihai (Logic, Architecture, Requirements)

**Engineering:** AI-assisted refactoring via Claude & Gemini

An automated monitoring tool for Linux servers that scans a specified directory for application instances (identified by a naming convention), then for each instance verifies that a log file exists, is recent within a configurable time threshold, and contains a specific success string confirming a completed sync. Results are output to both the console and a timestamped log file, which is automatically renamed to indicate failure if any check does not pass. The script runs once and exits immediately.

The tool is designed to run per-host, not as a centralized scanner. Typical deployment assumes tens of instances per server, with horizontal scaling achieved by running the script independently on multiple nodes.

Performance: Typical execution time is under 10 seconds for ~10–50 instances per host. Execution is I/O bound and scales linearly with number of instances and log file size; no network calls or external dependencies are involved.

Log files are expected in /logs/ subdirectory of each instance and must match *.log . 

A log file is considered recent if its last modification timestamp (mtime) is within the last N minutes (default: 15) relative to script execution time.

Table-sync detection uses a regex pattern matching numeric ID pairs in the format DDD+/DDD+ (e.g. 1234/5678) to identify synchronization events in log streams.

**Problem Statement/What it actually solves:**
Standard monitoring tools only tell you if a service is 'Up' or 'Down'. They miss silent failures, cases where the app is running, but synchronization has stalled. Previously, this required 2+ hours of manual, error-prone log checking every day.
This tool replaces that manual grind with a server-level automation that audits log freshness and sync success patterns. It effectively eliminates human error and ensures that 'active' services are actually doing their job, not just idling while data stays stuck.

---

## Features
- **Automatic Discovery:** Scans a base directory for instances ending in `_LTD` and sorts them alphabetically.
- **Log Freshness Check:** Ensures the application is actively writing logs within a configurable time threshold (SLA monitoring).
- **Content Validation:** Verifies that the synchronization process has finished successfully by scanning the log tail for specific patterns.
- **Fail-Safe Logging:** Generates its own timestamped logs. If any instance fails, the script log is automatically renamed with a `_FAILED` suffix for immediate RCA (Root Cause Analysis).
- **Production Ready:** Uses `os._exit()` for a guaranteed hard stop, preventing lingering processes in high-availability environments.
- **Regex Powered:** Uses optimized Regular Expressions to scan for Tririga sync patterns and specific table-sync activity.

---

## Installation & Usage

No external dependencies required (uses standard Python 3.x libraries).

1. Clone this repository or download `instance_health_monitor.py`.
2. Ensure the script has execution permissions:
    ```bash
    chmod +x instance_health_monitor.py
    ```
3. Run with default settings:
    ```bash
    python3 instance_health_monitor.py
    ```
4. Run with custom parameters:
    ```bash
    python3 instance_health_monitor.py --base-dir /custom/path --threshold 30
    ```

---

## Exit Codes
- **Code 0 (OK):** All discovered instances passed all checks (Fresh log + Sync confirmed).
- **Code 1 (FAILURE):** One or more instances failed a check. Script log is saved as `*_FAILED.log`.
- **Code 2 (CRITICAL):** No `*_LTD` directories found in the base path. Configuration issue.

---

## Preview
- **Online Compiler:** The script logic can be previewed on external sites such as [PlayCode Python Compiler](https://playcode.io/python-compiler).

## Output demo
<img width="1440" height="2866" alt="image" src="https://github.com/user-attachments/assets/cdafb017-f5a4-4336-a40f-06eadc624e5d" />
