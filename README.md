# Application Instance Monitor

**Author:** Mihai (Logic, Architecture, Requirements)

**Engineering:** AI-assisted refactoring via Claude & Gemini

An automated monitoring tool for Linux servers that scans a specified directory for application instances (identified by a naming convention), then for each instance verifies that a log file exists, is recent within a configurable time threshold, and contains a specific success string confirming a completed sync. Results are output to both the console and a timestamped log file, which is automatically renamed to indicate failure if any check does not pass. The script runs once and exits immediately.

#Problem Statement
Manual validation of instance logs across multiple servers is time-consuming and error-prone. This tool eliminates that overhead by automating the entire check at the server level. It is particularly effective at catching silent sync failures — scenarios where services appear active but log files have stopped being updated — which are invisible to standard uptime monitors.

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
