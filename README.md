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
- Dockerized: fully containerized for portable deployment across different Linux distributions without Python environment management
- Kubernetes-ready: deployable as a diagnostic Pod within a cluster
## Usage
 
This tool can be run as a standalone Python script, via Docker, or as a Kubernetes Pod.
 
---
 
### Option A: Standalone Script
 
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
 
### Option B: Docker
 
Containerization ensures a consistent environment and simplifies timezone management.
 
1. **Build the image:**
   ```bash
   docker build -t health-monitor .
   ```
 
2. **Run the monitor:**
   ```bash
   docker run --rm \
     -v /etc/localtime:/etc/localtime:ro \
     -v /opt/apps/Company:/opt/apps/Company \
     health-monitor
   ```
 
> [!IMPORTANT]
> **Timezone Sync:** The `-v /etc/localtime:/etc/localtime:ro` flag is critical.
> It ensures the container uses the host's system time.
> Without this, the freshness check (mtime) might fail if the container defaults to UTC while your logs are in local time.
 
*Note: Replace `/opt/apps/Company` with your actual instances path.*
 
---
 
### Option C: Kubernetes (Cloud-Native Deployment)
 
The tool is Kubernetes-ready, allowing you to run it as a diagnostic Pod within a cluster. This is ideal for environments where application instances are managed across K8s nodes.
 
1. **Build and load the image into Minikube:**
   ```bash
   docker build -t health-monitor:v2 .
   minikube image load health-monitor:v2
   ```
 
2. **Mount the instances directory (keep this terminal open):**
   ```bash
   minikube mount /opt/apps/Company:/opt/apps/Company
   ```
 
3. **Deploy the Pod:**
   ```bash
   kubectl apply -f monitor-pod.yaml
   ```
 
4. **Check execution results:**
   ```bash
   kubectl logs instance-monitor
   ```
 
> [!NOTE]
> The `minikube mount` process must stay alive in a separate terminal for the volume to remain accessible inside the cluster.
 
---
 
## Exit Codes
 
- **Code 0 (OK):** All discovered instances passed all checks (Fresh log + Sync confirmed).
- **Code 1 (FAILURE):** One or more instances failed a check. Script log is saved as `*_FAILED.log`.
- **Code 2 (CRITICAL):** No `*_LTD` directories found in the base path. Configuration issue.
---
 
## Output Demo

Real execution output captured from a Kubernetes Pod deployment via `kubectl logs`.

### ❌ Failure detected — sync confirmation missing

```text
=====================================================================================
  Company Instance Monitor
  Started at     : 2026-05-14 05:32:21
  Base directory : /opt/apps/Company
  Threshold      : 15 minutes
=====================================================================================

Instances found: 1
  1. Instance1_LTD

---------------------------------------------
  Checking: Instance1_LTD
---------------------------------------------
    **** ERROR: 'Tririga Finished Synch Succesfully' not found in last 1000 lines ****

=====================================================================================
  SUMMARY
=====================================================================================
  [FAIL] Instances where Tririga sync was NOT confirmed:
    1. Instance1_LTD  ->  'Tririga Finished Synch Succesfully' not found in last 1000 lines

=====================================================================================
  Finished at         : 2026-05-14 05:32:21
  Total instances     : 1
  OK                  : 0
  Failed              : 1
=====================================================================================
```

### ✅ All instances healthy

```text
=====================================================================================
  Company Instance Monitor
  Started at     : 2026-05-14 07:23:53
  Base directory : /opt/apps/Company
  Threshold      : 15 minutes
=====================================================================================

Instances found: 1
  1. Instance1_LTD

---------------------------------------------
  Checking: Instance1_LTD
---------------------------------------------
    [OK] Log is fresh and Tririga sync confirmed.

=====================================================================================
  SUMMARY
=====================================================================================
  [OK] Instances fully healthy:
    1. Instance1_LTD

=====================================================================================
  Finished at         : 2026-05-14 07:23:53
  Total instances     : 1
  OK                  : 1
  Failed              : 0
=====================================================================================
```
> This output demonstrates failure detection working correctly — the instance was discovered, checked, and the missing sync confirmation was flagged for RCA.
 
---
 
## Visual Output Demo
<img width="1440" height="2866" alt="image" src="https://github.com/user-attachments/assets/cdafb017-f5a4-4336-a40f-06eadc624e5d" />
