"""What the app asks of the computer: open a file, show a notification, run the search every day.

Standard library only, for Windows, Mac and Linux.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

TASK_NAME = "Retrieve Job"  # name of the daily task in the Windows Task Scheduler
_CRON_MARK = "# retrieve-job daily search"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def open_file(path: Path) -> None:
    """Opens a file in its usual app (Excel, LibreOffice, Numbers...)."""
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def notify(title: str, message: str) -> None:
    """A notification in the corner of the screen; does nothing if the system refuses it."""
    try:
        if os.name == "nt":
            def quoted(text: str) -> str:
                return "'" + text.replace("'", "''") + "'"
            script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] > $null;"
                "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$xml.GetElementsByTagName('text').Item(0).InnerText = {quoted(title)};"
                f"$xml.GetElementsByTagName('text').Item(1).InnerText = {quoted(message)};"
                # Windows only shows notifications from known apps: this one is PowerShell's
                "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show("
                "[Windows.UI.Notifications.ToastNotification]::new($xml))"
            )
            subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             creationflags=_NO_WINDOW)
        elif sys.platform == "darwin":
            subprocess.Popen(["osascript", "-e", f"display notification {_applescript(message)} "
                                                 f"with title {_applescript(title)}"])
        else:
            subprocess.Popen(["notify-send", title, message])
    except OSError:
        pass


def flash_window(window_id: int) -> None:
    """Makes the window's taskbar button blink until you come back to it (Windows only)."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    class FlashInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.UINT), ("window", wintypes.HWND), ("flags", wintypes.DWORD),
                    ("count", wintypes.UINT), ("timeout", wintypes.DWORD)]
    window = ctypes.windll.user32.GetParent(window_id)  # tkinter gives its inner frame: the real window is above
    info = FlashInfo(ctypes.sizeof(FlashInfo), window, 3 | 12, 0, 0)  # caption and taskbar, until in front
    ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))


_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def scheduled() -> dict | None:
    """When the automatic search runs, or None when it isn't planned.

    {"hour": 9, "minute": 30, "every_days": 2, "weekdays": []}: every 2 days at 9:30;
    {"hour": 9, "minute": 30, "every_days": 0, "weekdays": [0, 3]}: on Mondays and Thursdays at 9:30.
    """
    try:
        if os.name == "nt":
            result = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME, "/XML"], capture_output=True,
                                    text=True, creationflags=_NO_WINDOW)
            return _from_task_xml(result.stdout) if result.returncode == 0 else None
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        return _from_cron(result.stdout)
    except OSError:
        return None


def schedule(plan: dict, command: list[str]) -> str:
    """Runs command as plan says (see scheduled()); returns "" when done, otherwise what went wrong."""
    hour, minute = plan["hour"] % 24, plan["minute"] % 60
    try:
        if os.name == "nt":
            if plan["weekdays"]:
                days = ",".join(_WEEKDAYS[day][:3].upper() for day in sorted(plan["weekdays"]))
                when = ["/SC", "WEEKLY", "/D", days]
            else:
                when = ["/SC", "DAILY", "/MO", str(max(1, plan["every_days"]))]
            line = " ".join(f'"{part}"' for part in command)
            result = subprocess.run(["schtasks", "/Create", "/F", *when, "/ST", f"{hour:02d}:{minute:02d}",
                                     "/TN", TASK_NAME, "/TR", line], capture_output=True, text=True,
                                    creationflags=_NO_WINDOW)
            return "" if result.returncode == 0 else (result.stderr or result.stdout).strip()
        if plan["weekdays"]:  # cron counts the days from Sunday = 0
            days = "* * " + ",".join(str((day + 1) % 7) for day in sorted(plan["weekdays"]))
        else:
            days = f"*/{max(1, plan['every_days'])} * *"
        line = " ".join(_shell_quoted(part) for part in command)
        return _set_crontab(f"{minute} {hour} {days} {line} >/dev/null 2>&1 {_CRON_MARK}")
    except OSError as exc:
        return str(exc)


def _from_task_xml(xml: str) -> dict | None:
    start = re.search(r"<StartBoundary>[^T<]*T(\d{2}):(\d{2})", xml)
    if not start:
        return None
    plan = {"hour": int(start.group(1)), "minute": int(start.group(2)), "every_days": 0, "weekdays": []}
    week = re.search(r"<DaysOfWeek>(.*?)</DaysOfWeek>", xml, re.DOTALL)
    if week:
        plan["weekdays"] = [index for index, name in enumerate(_WEEKDAYS) if f"<{name}" in week.group(1)]
    else:
        interval = re.search(r"<DaysInterval>(\d+)</DaysInterval>", xml)
        plan["every_days"] = int(interval.group(1)) if interval else 1
    return plan


def _from_cron(crontab: str) -> dict | None:
    match = re.search(rf"^(\d+) (\d+) (\S+) \S+ (\S+) .*{re.escape(_CRON_MARK)}$", crontab, re.MULTILINE)
    if not match:
        return None
    minute, hour, day_of_month, day_of_week = match.groups()
    plan = {"hour": int(hour), "minute": int(minute), "every_days": 0, "weekdays": []}
    if day_of_week != "*":
        plan["weekdays"] = sorted((int(day) - 1) % 7 for day in day_of_week.split(","))
    else:
        plan["every_days"] = int(day_of_month[2:]) if day_of_month.startswith("*/") else 1
    return plan


def unschedule() -> str:
    """Stops the automatic search; returns "" when done, otherwise what went wrong."""
    try:
        if os.name == "nt":
            result = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True,
                                    text=True, creationflags=_NO_WINDOW)
            return "" if result.returncode == 0 else (result.stderr or result.stdout).strip()
        return _set_crontab(None)
    except OSError as exc:
        return str(exc)


def _set_crontab(new_line: str | None) -> str:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    lines = [line for line in current.splitlines() if not line.endswith(_CRON_MARK)]
    if new_line:
        lines.append(new_line)
    result = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True)
    return "" if result.returncode == 0 else result.stderr.strip()


def _shell_quoted(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _applescript(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
