# Application Instance Monitor
Author      : Mihai (Logic, Architecture, Requirements)
Engineering : AI-assisted refactoring via Claude & Gemini

A robust Python-based monitoring tool designed to verify the health of application instances on Linux servers. It checks for log existence, file modification freshness (SLA), and specific success strings within log files.

## Features
- **Automatic Discovery:** Scans a base directory for instances ending in `_LTD`.
- **Log Freshness Check:** Ensures the application is actively writing logs within a configurable time threshold.
- **Content Validation:** Verifies that the synchronization or main process has finished successfully by scanning the log tail.
- **Detailed Logging:** Generates its own timestamped logs, including a `_FAILED` suffix if issues are detected.

## Installation
No external dependencies required (uses standard Python 3 libraries).
1. Clone this repository or download `instance_health_monitor.py`.
2. Ensure the script has execution permissions:
   ```bash
   chmod +x app_log_monitor.py
## Preview
It can be ran on external sites such as https://playcode.io/python-compiler 
