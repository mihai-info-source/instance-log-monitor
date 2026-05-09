# Application Instance Monitor

**Author:** Mihai (Logic, Architecture, Requirements)  
**Engineering:** AI-assisted refactoring via Claude & Gemini

A robust Python-based monitoring tool designed to verify the health of application instances on Linux (Red Hat) servers. It automates the verification of log existence, file modification freshness (SLA), and specific success strings within log files.

---

## Features
- **Automatic Discovery:** Scans a base directory for instances ending in `_LTD` and sorts them alphabetically.
- **Log Freshness Check:** Ensures the application is actively writing logs within a configurable time threshold (SLA monitoring).
- **Content Validation:** Verifies that the synchronization process has finished successfully by scanning the log tail for specific patterns.
- **Fail-Safe Logging:** Generates its own timestamped logs. If any instance fails, the script log is automatically renamed with a `_FAILED` suffix for immediate RCA (Root Cause Analysis).
- **Production Ready:** Uses `os._exit()` for a guaranteed hard stop, preventing lingering processes in high-availability environments.

---

## Installation & Usage

No external dependencies required (uses standard Python 3.x libraries).

1. Clone this repository or download `instance_health_monitor.py`.
2. Ensure the script has execution permissions:
   ```bash
   chmod +x instance_health_monitor.py
