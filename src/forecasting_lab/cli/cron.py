"""CLI: schedule the orchestrator to run automatically.

On Windows this registers a real Task Scheduler job (via ``schtasks``) that runs
``flab-run-all`` daily. On macOS/Linux it prints the crontab line to add (cron
edits are best done by hand). Examples::

    python -m forecasting_lab.cli.cron install --time 07:30
    python -m forecasting_lab.cli.cron status
    python -m forecasting_lab.cli.cron uninstall

The job runs the whole pipeline suite and rebuilds the dashboard. It touches the
network on your schedule — remove it any time with ``uninstall``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from ..config import PATHS

TASK_NAME = "ForecastingLabDaily"


def _run_command() -> str:
    # Use the current interpreter so the task runs in the same environment.
    return f'"{sys.executable}" -m forecasting_lab.cli.run_all'


def _cron_line(time_hhmm: str) -> str:
    hh, mm = time_hhmm.split(":")
    return f"{int(mm)} {int(hh)} * * *  cd {PATHS.root} && {_run_command()}  >> {PATHS.root}/cron.log 2>&1"


def _install_windows(time_hhmm: str) -> int:
    cmd = [
        "schtasks", "/Create", "/TN", TASK_NAME, "/SC", "DAILY", "/ST", time_hhmm,
        "/TR", f'cmd /c "cd /d {PATHS.root} && {_run_command()}"', "/F",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout.strip() or result.stderr.strip())
    if result.returncode == 0:
        print(f"Installed daily task '{TASK_NAME}' at {time_hhmm}. Remove with: cron uninstall")
    return result.returncode


def _uninstall_windows() -> int:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True, text=True
    )
    print(result.stdout.strip() or result.stderr.strip())
    return result.returncode


def _status_windows() -> int:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME], capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"No scheduled task '{TASK_NAME}'. Install with: cron install")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    inst = sub.add_parser("install", help="schedule the daily orchestrator run")
    inst.add_argument("--time", default="07:30", help="HH:MM local time (default 07:30)")
    sub.add_parser("uninstall", help="remove the scheduled job")
    sub.add_parser("status", help="show the scheduled job")
    args = ap.parse_args(argv)

    is_windows = sys.platform.startswith("win")

    if args.cmd == "install":
        if is_windows:
            return _install_windows(args.time)
        print("Add this line to your crontab (`crontab -e`):\n")
        print("  " + _cron_line(args.time))
        return 0
    if args.cmd == "uninstall":
        if is_windows:
            return _uninstall_windows()
        print(f"Remove the crontab line that runs '{TASK_NAME.lower()}' / flab-run-all.")
        return 0
    if args.cmd == "status":
        if is_windows:
            return _status_windows()
        print("On POSIX, check `crontab -l` for the flab-run-all line.")
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
