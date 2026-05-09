#!/usr/bin/env python3
"""
================================================================================
Company Instance Monitor
================================================================================
EN: Monitors Company application instances on Linux (Red Hat) servers.
    For each instance directory ending in _LTD, the script verifies:
      1. That a .log file exists inside the instance's /logs/ subfolder.
      2. That the most recent log file has been updated within the threshold.
      3. That the log contains the Tririga sync success string.
    Results are written to both the console and a timestamped log file.
    The script runs ONCE and exits immediately — it does NOT loop or linger.

RO: Monitorizează instanțele aplicației Company pe servere Linux (Red Hat).
    Pentru fiecare director de instanță care se termină în _LTD, scriptul verifică:
      1. Că există un fișier .log în subdirectorul /logs/ al instanței.
      2. Că cel mai recent fișier log a fost actualizat în intervalul de timp configurat.
      3. Că log-ul conține șirul de succes al sincronizării Tririga.
    Rezultatele sunt scrise atât în consolă cât și într-un fișier log cu timestamp.
    Scriptul rulează O SINGURĂ DATĂ și se oprește imediat — nu rulează în buclă.

--------------------------------------------------------------------------------
Author  : Mihai
Usage   : python3 Company_monitor.py
          python3 Company_monitor.py --base-dir /opt/apps/Company --threshold 15
--------------------------------------------------------------------------------
Exit codes / Coduri de ieșire:
    0  —  All instances OK
    1  —  One or more failures detected
    2  —  No instances found at all
================================================================================
"""

import os
import sys
import glob
import re
import argparse
import logging
from datetime import datetime, timedelta


# ============================================================
# SECTION 1 — Configuration constants / Constante de configurare
#
# EN: All tuneable values live here. Never hardcode these mid-script.
# RO: Toate valorile configurabile sunt aici. Nu le scrie niciodată direct în mijlocul scriptului.
# ============================================================

DEFAULT_BASE_DIR          = "/opt/apps/Company"  # Root folder for all instances / Directorul rădăcină al instanțelor
DEFAULT_THRESHOLD_MINUTES = 15                      # Max age of a log file in minutes / Vârsta maximă a log-ului în minute
DEFAULT_TAIL_LINES        = 1000                    # Lines to read from end of log / Linii citite de la sfârșitul log-ului
MTIME_TOLERANCE_SECONDS   = 2                       # Tolerance for float mtime comparison / Toleranță pentru compararea float mtime

# EN: Regex for table-sync log entries, e.g. "1234/5678".
#     \b = word boundary — avoids matching inside longer numeric strings.
#     {3,} = three or more digits on each side of the slash.
# RO: Regex pentru intrările de sincronizare tabel, ex: "1234/5678".
#     \b = limită de cuvânt — evită potriviri în interiorul șirurilor numerice mai lungi.
#     {3,} = trei sau mai multe cifre de fiecare parte a slash-ului.
SYNC_PATTERN = re.compile(r"\b\d{3,}/\d{3,}\b")

# EN: Success string searched in each log, matched case-insensitively.
#     "Succesfully" is intentionally misspelled to match the application's own typo.
# RO: Șirul de succes căutat în fiecare log, fără distincție majuscule.
#     "Succesfully" este intenționat greșit pentru a se potrivi cu typo-ul aplicației.
TRIRIGA_SUCCESS_MSG = "tririga finished synch succesfully"


# ============================================================
# SECTION 2 — Logging setup / Configurarea sistemului de logging
# ============================================================

def setup_logging(log_dir: str) -> tuple:
    """
    EN: Creates a logger that writes simultaneously to stdout and a timestamped .log file.
        Returns the logger and the base path of the log file (without extension),
        so the caller can rename it later if failures are detected.

    RO: Creează un logger care scrie simultan în stdout și într-un fișier .log cu timestamp.
        Returnează logger-ul și calea de bază a fișierului log (fără extensie),
        astfel încât apelantul să poată redenumi fișierul dacă sunt detectate erori.

    Args:
        log_dir (str): Directory where script log files are stored.
                       Directorul unde sunt stocate fișierele log ale scriptului.

    Returns:
        tuple: (logger, log_file_base_path)
    """
    os.makedirs(log_dir, exist_ok=True)

    # EN: Hyphens in the time part — colons are invalid in filenames on some filesystems.
    # RO: Cratime în partea de timp — două puncte sunt invalide în nume de fișiere pe unele sisteme.
    timestamp     = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_file_base = os.path.join(log_dir, timestamp)
    log_file_path = f"{log_file_base}.log"

    logger = logging.getLogger("Company_monitor")
    logger.setLevel(logging.DEBUG)

    # EN: Plain formatter — no level prefix, just the raw message text.
    # RO: Formatter simplu — fără prefix de nivel, doar textul brut al mesajului.
    fmt = logging.Formatter("%(message)s")

    # EN: Console handler — mirrors output to stdout so cron jobs can capture it.
    # RO: Handler consolă — oglindește output-ul în stdout, util și pentru job-uri cron.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # EN: File handler — writes the same output to the timestamped log file on disk.
    # RO: Handler fișier — scrie același output în fișierul log cu timestamp de pe disc.
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger, log_file_base


# ============================================================
# SECTION 3 — Helper functions / Funcții ajutătoare
# ============================================================

def tail_lines(filepath: str, n: int = DEFAULT_TAIL_LINES) -> list:
    """
    EN: Returns the last *n* lines of a file.
        Reads the full file but discards all but the tail.
        Non-UTF-8 bytes are silently replaced so encoding issues never crash the script.

    RO: Returnează ultimele *n* linii ale unui fișier.
        Citește fișierul complet dar păstrează doar coada.
        Bytes non-UTF-8 sunt înlocuiți silențios pentru ca problemele de encoding să nu oprească scriptul.

    Args:
        filepath (str): Absolute path to the log file. / Calea absolută spre fișierul log.
        n        (int): Number of lines to return.    / Numărul de linii de returnat.

    Returns:
        list[str]: The last n lines.   / Ultimele n linii.

    Raises:
        OSError: If the file cannot be opened. / Dacă fișierul nu poate fi deschis.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()[-n:]
    except OSError as exc:
        raise OSError(f"Cannot read '{filepath}': {exc}") from exc


def find_instances(base_dir: str) -> list:
    """
    EN: Scans base_dir one level deep and returns a sorted list of directory paths
        whose name ends exactly with '_LTD'. Files are excluded — directories only.
        Alphabetical sort satisfies Requirement 1 (numbered, ordered discovery list).

    RO: Scanează base_dir un singur nivel și returnează o listă sortată de căi de directoare
        al căror nume se termină exact cu '_LTD'. Fișierele sunt excluse — doar directoare.
        Sortarea alfabetică satisface Cerința 1 (listă de descoperire numerotată, ordonată).

    Args:
        base_dir (str): Root directory to scan. / Directorul rădăcină de scanat.

    Returns:
        list[str]: Sorted absolute directory paths. / Căi absolute de directoare sortate.
    """
    return sorted(
        entry
        for entry in glob.glob(os.path.join(base_dir, "*_LTD"))
        if os.path.isdir(entry)  # EN: directories only / RO: doar directoare
    )


def find_latest_logs(log_dir: str) -> list:
    """
    EN: Returns all .log files in log_dir that share the most recent modification time,
        within a tolerance of MTIME_TOLERANCE_SECONDS.

        Handles the tie-breaker case from Requirement 2: when multiple log files
        exist at the same timestamp, ALL are returned so their content is checked.

        Using a tolerance instead of strict float equality avoids a common bug on
        filesystems that round modification times to the nearest second.

    RO: Returnează toate fișierele .log din log_dir care împart cel mai recent timp de modificare,
        în limita MTIME_TOLERANCE_SECONDS.

        Gestionează cazul de egalitate din Cerința 2: când mai multe fișiere log există
        la același timestamp, TOATE sunt returnate pentru a fi verificate.

        Folosirea toleranței în loc de egalitate strictă float evită un bug comun pe
        sistemele de fișiere care rotunjesc timpii de modificare la cel mai apropiat secundă.

    Args:
        log_dir (str): Path to the instance logs/ folder. / Calea spre folderul logs/ al instanței.

    Returns:
        list[str]: Paths sharing the newest mtime, or [] if no .log files exist.
                   Căi cu cel mai recent mtime, sau [] dacă nu există fișiere .log.
    """
    candidates = glob.glob(os.path.join(log_dir, "*.log"))
    if not candidates:
        return []

    # EN: Identify the newest modification time across all candidate files.
    # RO: Identificăm cel mai recent timp de modificare din toate fișierele candidate.
    max_mtime = max(os.path.getmtime(f) for f in candidates)

    # EN: Collect every file whose mtime falls within tolerance of that maximum.
    #     abs() + tolerance avoids the float == float trap.
    # RO: Colectăm fiecare fișier al cărui mtime se află în toleranța față de maxim.
    #     abs() + toleranță evită capcana float == float.
    return [
        f for f in candidates
        if abs(os.path.getmtime(f) - max_mtime) <= MTIME_TOLERANCE_SECONDS
    ]


def is_recently_modified(filepath: str, threshold: datetime) -> bool:
    """
    EN: Returns True if the file was last modified at or after *threshold*.
        Determines whether a log file counts as "fresh" for the current check run.

    RO: Returnează True dacă fișierul a fost modificat ultima dată la sau după *threshold*.
        Determină dacă un fișier log este considerat "proaspăt" pentru rularea curentă.

    Args:
        filepath  (str)      : Path to the file.           / Calea fișierului.
        threshold (datetime) : Minimum acceptable mtime.   / Timp minim acceptabil de modificare.

    Returns:
        bool: True if fresh, False if stale. / True dacă e recent, False dacă e vechi.
    """
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    return mtime >= threshold


# ============================================================
# SECTION 4 — Per-instance check / Verificarea per instanță
# ============================================================

def check_instance(instance_path: str, threshold: datetime,
                   threshold_min: int, logger: logging.Logger) -> dict:
    """
    EN: Runs all three checks for a single Company instance and returns a result dict.

        Check 1 — Log existence:
            Looks for *.log files inside <instance_path>/logs/.
            Returns status "log_missing" if none are found.

        Check 2 — Log freshness:
            Uses find_latest_logs() to get the newest file(s).
            Returns status "log_stale" if the newest mtime is older than threshold.
            If multiple files share the same timestamp (tie), ALL are read in Check 3.

        Check 3 — Tririga sync confirmation:
            Reads the last DEFAULT_TAIL_LINES lines of each candidate file.
            Returns status "tririga_error" if TRIRIGA_SUCCESS_MSG is not found.
            Also detects table-sync entries (SYNC_PATTERN) but only in lines
            whose embedded timestamp falls within the current threshold window.

        Never raises — all OSErrors are caught and returned as "read_error" status.

    RO: Rulează toate cele trei verificări pentru o singură instanță Company și returnează un dict.

        Verificare 1 — Existența log-ului:
            Caută fișiere *.log în <instance_path>/logs/.
            Returnează status "log_missing" dacă nu sunt găsite.

        Verificare 2 — Prospețimea log-ului:
            Folosește find_latest_logs() pentru a obține cel(e) mai nou(ă) fișier(e).
            Returnează status "log_stale" dacă cel mai recent mtime e mai vechi decât threshold.
            Dacă mai multe fișiere împart același timestamp (egalitate), TOATE sunt citite în Verificarea 3.

        Verificare 3 — Confirmarea sincronizării Tririga:
            Citește ultimele DEFAULT_TAIL_LINES linii din fiecare fișier candidat.
            Returnează status "tririga_error" dacă TRIRIGA_SUCCESS_MSG nu este găsit.
            Detectează și intrările de sincronizare tabel (SYNC_PATTERN) dar doar în linii
            al căror timestamp embedded se încadrează în fereastra de timp curentă.

        Nu aruncă niciodată excepții — toate OSError-urile sunt prinse și returnate ca status "read_error".

    Args:
        instance_path (str)            : Absolute path to the *_LTD directory.
                                         Calea absolută spre directorul *_LTD.
        threshold     (datetime)       : Cutoff datetime for log freshness.
                                         Datetime limită pentru prospețimea log-ului.
        threshold_min (int)            : Threshold in minutes, used to build the line-filter string.
                                         Pragul în minute, folosit pentru șirul de filtrare al liniilor.
        logger        (logging.Logger) : Logger for inline error output.
                                         Logger pentru output de eroare inline.

    Returns:
        dict with keys / dict cu cheile:
            name        (str)  : Instance directory name.
            status      (str)  : "ok" | "log_missing" | "log_stale" | "tririga_error" | "read_error"
            tririga_ok  (bool) : True if the success string was found.
            table_sync  (bool) : True if recent table-sync entries were detected.
            error_msg   (str)  : Human-readable failure reason, or "" if OK.
    """
    name     = os.path.basename(instance_path)
    log_path = os.path.join(instance_path, "logs")

    # ------------------------------------------------------------------
    # Check 1 — Log existence / Verificare 1 — Existența log-ului
    # ------------------------------------------------------------------
    candidate_logs = find_latest_logs(log_path)

    if not candidate_logs:
        return {
            "name"      : name,
            "status"    : "log_missing",
            "tririga_ok": False,
            "table_sync": False,
            "error_msg" : "No .log file found in logs/ directory",
        }

    # ------------------------------------------------------------------
    # Check 2 — Log freshness / Verificare 2 — Prospețimea log-ului
    #
    # EN: All files in candidate_logs share the same mtime (within tolerance),
    #     so checking the first file is sufficient for the freshness test.
    # RO: Toate fișierele din candidate_logs împart același mtime (în toleranță),
    #     deci verificarea primului fișier este suficientă pentru testul de prospețime.
    # ------------------------------------------------------------------
    if not is_recently_modified(candidate_logs[0], threshold):
        return {
            "name"      : name,
            "status"    : "log_stale",
            "tririga_ok": False,
            "table_sync": False,
            "error_msg" : (
                f"Log not updated since {threshold.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(threshold: {threshold_min} min)"
            ),
        }

    # ------------------------------------------------------------------
    # Check 3 — Tririga sync content / Verificare 3 — Conținutul sincronizării Tririga
    #
    # EN: cutoff_str is an ISO hour prefix (e.g. "2025-05-09T14") used to filter
    #     table-sync lines to only those written in the current threshold window.
    #     This prevents counting old sync events from earlier in the same day.
    # RO: cutoff_str este un prefix ISO al orei (ex: "2025-05-09T14") folosit pentru a filtra
    #     liniile de sincronizare tabel la cele scrise în fereastra de timp curentă.
    #     Previne numărarea evenimentelor vechi de sincronizare din aceeași zi.
    # ------------------------------------------------------------------
    cutoff_str = (
        datetime.now() - timedelta(minutes=threshold_min)
    ).strftime("%Y-%m-%dT%H")

    tririga_ok = False
    table_sync = False

    try:
        for log_file in candidate_logs:
            lines = tail_lines(log_file)

            for line in lines:
                # EN: Tririga check — scans the full tail; the success message can appear anywhere.
                # RO: Verificare Tririga — scanează întregul tail; mesajul de succes poate apărea oriunde.
                if TRIRIGA_SUCCESS_MSG in line.lower():
                    tririga_ok = True

                # EN: Table-sync check — only flag lines carrying a recent timestamp.
                # RO: Verificare sincronizare tabel — marcăm doar liniile cu timestamp recent.
                if cutoff_str in line and SYNC_PATTERN.search(line):
                    table_sync = True

            # EN: Short-circuit — stop reading further files once success is confirmed.
            # RO: Scurtcircuit — oprim citirea altor fișiere odată ce succesul e confirmat.
            if tririga_ok:
                break

    except OSError as exc:
        logger.error(f"    **** ERROR: Could not read log file — {exc} ****")
        return {
            "name"      : name,
            "status"    : "read_error",
            "tririga_ok": False,
            "table_sync": False,
            "error_msg" : f"Could not read log file: {exc}",
        }

    if not tririga_ok:
        return {
            "name"      : name,
            "status"    : "tririga_error",
            "tririga_ok": False,
            "table_sync": table_sync,
            "error_msg" : (
                f"'Tririga Finished Synch Succesfully' not found "
                f"in last {DEFAULT_TAIL_LINES} lines"
            ),
        }

    return {
        "name"      : name,
        "status"    : "ok",
        "tririga_ok": True,
        "table_sync": table_sync,
        "error_msg" : "",
    }


# ============================================================
# SECTION 5 — CLI argument parsing / Parsarea argumentelor CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    """
    EN: Defines and parses optional command-line arguments.
        Defaults are pulled from Section 1 constants so the script works
        out of the box without any arguments on any server.

    RO: Definește și parsează argumentele opționale din linia de comandă.
        Valorile implicite vin din constantele din Secțiunea 1, astfel încât scriptul
        funcționează fără niciun argument pe orice server.

    Returns:
        argparse.Namespace: Parsed arguments. / Argumente parsate.
    """
    parser = argparse.ArgumentParser(
        description="Monitor Company *_LTD instances: checks log freshness and Tririga sync.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        metavar="PATH",
        help=f"Root directory containing *_LTD instance folders (default: {DEFAULT_BASE_DIR})",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD_MINUTES,
        metavar="MINUTES",
        help=f"Minutes within which log files must have been updated (default: {DEFAULT_THRESHOLD_MINUTES})",
    )
    return parser.parse_args()


# ============================================================
# SECTION 6 — Hard exit / Oprire forțată
# ============================================================

def _hard_exit(logger: logging.Logger, log_file_base: str, exit_code: int) -> None:
    """
    EN: Flushes and closes all log handlers, renames the log file to *_FAILED.log
        if exit_code is non-zero, then calls os._exit() for an immediate hard stop.

        os._exit() bypasses:
          - Python's normal interpreter shutdown
          - All atexit registered handlers
          - All __del__ finalizers
          - Any pending finally blocks above this call

        This satisfies Requirement 4: the script cannot continue running
        under any circumstance after this function is called.

    RO: Golește și închide toți handlerii de log, redenumește fișierul log în *_FAILED.log
        dacă exit_code nu este zero, apoi apelează os._exit() pentru o oprire imediată forțată.

        os._exit() ocolește:
          - Oprirea normală a interpretorului Python
          - Toți handlerii înregistrați cu atexit
          - Toți finalizatorii __del__
          - Orice blocuri finally pendinte deasupra acestui apel

        Aceasta satisface Cerința 4: scriptul nu poate continua să ruleze
        în nicio circumstanță după apelarea acestei funcții.

    Args:
        logger        (logging.Logger) : Logger to flush and close.   / Logger-ul de închis.
        log_file_base (str)            : Log file base path, no ext.  / Calea de bază, fără extensie.
        exit_code     (int)            : 0 = OK, 1 = failure, 2 = no instances found.
    """
    current_log = f"{log_file_base}.log"

    # EN: Flush and close all handlers before touching the file on disk.
    # RO: Golim și închidem toți handlerii înainte de a atinge fișierul pe disc.
    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)

    if exit_code != 0:
        failed_log = f"{log_file_base}_FAILED.log"
        try:
            os.rename(current_log, failed_log)
            print(f"[RESULT] Failures detected. Log saved as: {os.path.basename(failed_log)}")
        except OSError as exc:
            print(f"[WARNING] Could not rename log file: {exc}")
    else:
        print(f"[RESULT] All checks passed. Log saved as: {os.path.basename(current_log)}")

    # EN: Hard stop — no further Python code executes after this line, guaranteed.
    # RO: Oprire forțată — niciun cod Python nu se mai execută după această linie, garantat.
    os._exit(exit_code)


# ============================================================
# SECTION 7 — Main orchestration / Orchestrarea principală
# ============================================================

def main() -> None:
    """
    EN: Orchestrates the full monitoring run:
          1. Parse arguments, create log directory, set up dual logging.
          2. Discover *_LTD directories; print them numbered alphabetically.
          3. Run three checks on every instance; print inline result per instance.
          4. Group results; print a numbered summary by outcome category.
          5. Hard-exit — the script never loops, sleeps, or lingers.

    RO: Orchestrează rularea completă a monitorizării:
          1. Parsează argumentele, creează directorul de log, configurează logging-ul dual.
          2. Descoperă directoarele *_LTD; le afișează numerotate alfabetic.
          3. Rulează trei verificări pe fiecare instanță; afișează rezultatul per instanță.
          4. Grupează rezultatele; afișează un sumar numerotat pe categorii de rezultat.
          5. Oprire forțată — scriptul nu rulează în buclă, nu doarme și nu continuă.
    """
    args     = parse_args()
    base_dir = args.base_dir
    log_dir  = os.path.join(base_dir, "script_logs")

    logger, log_file_base = setup_logging(log_dir)

    SEP  = "=" * 85
    SEP2 = "-" * 45

    # --- Header ---
    logger.info(SEP)
    logger.info("  Company Instance Monitor")
    logger.info(f"  Started at     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Base directory : {base_dir}")
    logger.info(f"  Threshold      : {args.threshold} minutes")
    logger.info(SEP)
    logger.info("")

    # ------------------------------------------------------------------
    # Step 1 — Discover instances
    # EN: Scan for *_LTD directories and print them numbered alphabetically.
    # RO: Scanăm directoarele *_LTD și le afișăm numerotate alfabetic.
    # ------------------------------------------------------------------
    instances = find_instances(base_dir)

    if not instances:
        logger.error(f"**** FATAL: No *_LTD directories found in '{base_dir}'. Exiting. ****")
        _hard_exit(logger, log_file_base, exit_code=2)

    logger.info(f"Instances found: {len(instances)}")
    for idx, inst_path in enumerate(instances, start=1):
        logger.info(f"  {idx}. {os.path.basename(inst_path)}")
    logger.info("")

    # ------------------------------------------------------------------
    # Step 2 — Check each instance
    # EN: Run all three checks per instance and collect structured results.
    # RO: Rulăm toate trei verificările per instanță și colectăm rezultate structurate.
    # ------------------------------------------------------------------
    threshold = datetime.now() - timedelta(minutes=args.threshold)
    results   = []

    for inst_path in instances:
        name = os.path.basename(inst_path)
        logger.info(SEP2)
        logger.info(f"  Checking: {name}")
        logger.info(SEP2)

        result = check_instance(inst_path, threshold, args.threshold, logger)
        results.append(result)

        if result["status"] == "ok":
            logger.info("    [OK] Log is fresh and Tririga sync confirmed.")
        else:
            logger.info(f"    **** ERROR: {result['error_msg']} ****")

        if result["table_sync"]:
            logger.info(
                f"    [INFO] Table-sync entries detected in the last {args.threshold} min."
            )
        logger.info("")

    # ------------------------------------------------------------------
    # Step 3 — Build result groups
    # EN: Separate results into outcome categories for the summary section.
    # RO: Separăm rezultatele în categorii de rezultat pentru secțiunea de sumar.
    # ------------------------------------------------------------------
    ok_list         = [r for r in results if r["status"] == "ok"]
    missing_list    = [r for r in results if r["status"] == "log_missing"]
    stale_list      = [r for r in results if r["status"] == "log_stale"]
    tririga_err     = [r for r in results if r["status"] == "tririga_error"]
    read_err        = [r for r in results if r["status"] == "read_error"]
    table_sync_list = [r for r in results if r["table_sync"]]

    failure_detected = bool(missing_list or stale_list or tririga_err or read_err)

    # ------------------------------------------------------------------
    # Step 4 — Print summary
    # EN: Print each result group with numbered entries. Table-sync is
    #     informational only and never counts as a failure.
    # RO: Afișăm fiecare grup de rezultate cu intrări numerotate. Sincronizarea
    #     tabel este doar informativă și nu constituie niciodată o eroare.
    # ------------------------------------------------------------------
    logger.info(SEP)
    logger.info("  SUMMARY")
    logger.info(SEP)

    if table_sync_list:
        logger.info("  [INFO] Instances with recent table-sync activity (informational only):")
        for i, r in enumerate(sorted(table_sync_list, key=lambda x: x["name"]), 1):
            logger.info(f"    {i}. {r['name']}")
        logger.info("")

    failure_groups = [
        (missing_list, "Instances with NO log file found:"),
        (stale_list,   "Instances where log was NOT updated within the threshold:"),
        (tririga_err,  "Instances where Tririga sync was NOT confirmed:"),
        (read_err,     "Instances where log file could NOT be read:"),
    ]

    for group, label in failure_groups:
        if group:
            logger.info(f"  [FAIL] {label}")
            for i, r in enumerate(sorted(group, key=lambda x: x["name"]), 1):
                logger.info(f"    {i}. {r['name']}  ->  {r['error_msg']}")
            logger.info("")

    if ok_list:
        logger.info("  [OK] Instances fully healthy:")
        for i, r in enumerate(sorted(ok_list, key=lambda x: x["name"]), 1):
            logger.info(f"    {i}. {r['name']}")
        logger.info("")

    logger.info(SEP)
    logger.info(f"  Finished at         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Total instances     : {len(results)}")
    logger.info(f"  OK                  : {len(ok_list)}")
    logger.info(f"  Failed              : {len(results) - len(ok_list)}")
    logger.info(SEP)

    # EN: Hard exit — terminates the process immediately, satisfying Requirement 4.
    # RO: Ieșire forțată — termină procesul imediat, satisfăcând Cerința 4.
    _hard_exit(logger, log_file_base, exit_code=1 if failure_detected else 0)


# ============================================================
# SECTION 8 — Entry point guard / Gardă punct de intrare
#
# EN: main() runs only when the script is executed directly, not when imported.
#     This makes the module safe to import for unit testing without side effects.
# RO: main() rulează doar când scriptul este executat direct, nu când este importat.
#     Aceasta face modulul sigur de importat pentru teste unitare fără efecte secundare.
# ============================================================

if __name__ == "__main__":
    main()
