# Application Instance Monitor

**Author:** Mihai (Logic, Architecture, Requirements)

**Engineering:** AI-assisted refactoring via Claude & Gemini


## Overview

Standard monitoring systems typically report service availability (up/down), but fail to detect silent failures where services are running while critical synchronization processes are stalled.

This tool implements a log-based health inference system for Linux environments, focusing on functional correctness rather than process availability.


## How it works

The system scans a directory of application instances (based on naming convention) and performs the following checks per instance:

- Verifies presence of log files (`*.log` under `/logs/`)
- Validates log freshness using filesystem modification time (mtime-based threshold, default: 15 minutes)
- Confirms successful synchronization via log pattern matching

Results are printed to console and written to a timestamped execution log. If any check fails, the log file is automatically renamed with `_FAILED` for immediate RCA.



## Design & Architecture

- Designed for per-host execution, not centralized monitoring  
- Typically runs on servers with 10–50 instances  
- Horizontally scalable via deployment across multiple nodes  
- Fully I/O-bound (no network calls, no external dependencies)  
- Typical execution time: <10 seconds per host  


## Detection Logic

- **Freshness check:** filesystem mtime used as proxy for last log activity  
- **Sync validation:** log markers confirm completed synchronization  
- **Extended workload detection:** regex pattern `DDD+/DDD+` identifies batch synchronization activity, typically associated with large dataset refresh operations  


## Why it exists

Traditional monitoring systems focus on infrastructure health, but not execution state.

This tool was built to detect cases where:
- services appear healthy  
- but data synchronization is silently stalled  

It replaces manual log inspection (~2+ hours/day) with automated validation of system activity and functional correctness.



## Features

- Automatic instance discovery (`*_LTD`)
- Log freshness validation (SLA threshold-based)
- Sync success verification via log parsing
- Fail-safe logging with `_FAILED` tagging
- Regex-based detection of batch synchronization activity
- Single-run execution model (cron-friendly)
- Dockerized: Fully containerized for portable deployment across different Linux distributions without Python environment management

---


##  **Usage:**

This tool can be run as a standalone Python script or via Docker for improved isolation and portability.

### Option A: Standalone Script
No external dependencies required (uses standard Python 3.x libraries).

1. Clone this repository or download `instance_health_monitor.py`.
2. Ensure the script has execution permissions:
   ```bash
   chmod +x instance_health_monitor.py
3. Run with default settings:
    ```bash
    python3 instance_health_monitor.py
    ```
4. Run with custom parameters:
    ```bash
    python3 instance_health_monitor.py --base-dir /custom/path --threshold 30
    ```
    
### Option B: Docker (Recommended)
Containerization ensures a consistent environment and simplifies timezone management.

1. **Build the image:**
    ```bash
    docker build -t health-monitor .
    ```

2. **Run the monitor:**
    To work correctly, you must map your local instances directory and the system timezone to the container:
    
```bash
    docker run --rm \
      -v /etc/localtime:/etc/localtime:ro \
      -v /opt/apps/Company:/opt/apps/Company \
      health-monitor

    ```
    *Note: Replace `/opt/apps/Company` with your actual instances path.*
    ```
```

##  **Exit Codes:**
- **Code 0 (OK):** All discovered instances passed all checks (Fresh log + Sync confirmed).
- **Code 1 (FAILURE):** One or more instances failed a check. Script log is saved as `*_FAILED.log`.
- **Code 2 (CRITICAL):** No `*_LTD` directories found in the base path. Configuration issue.

---

## **Preview:**
- **Online Compiler:** The script logic can be previewed on external sites such as [PlayCode Python Compiler](https://playcode.io/python-compiler).

## Output demo
<img width="1440" height="2866" alt="image" src="https://github.com/user-attachments/assets/cdafb017-f5a4-4336-a40f-06eadc624e5d" />
