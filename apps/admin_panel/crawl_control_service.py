import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
PID_FILE = BASE_DIR / 'artifacts' / 'crawl_winmart_scheduler.json'


def _read_state():
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(pid):
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'pid': pid,
        'started_at': datetime.now().isoformat(timespec='seconds'),
    }
    PID_FILE.write_text(json.dumps(payload), encoding='utf-8')


def _clear_state():
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        return


def _is_pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False

    if os.name == 'nt':
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception:
            return False
        return str(pid) in (result.stdout or '')

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_crawl_scheduler_status():
    state = _read_state()
    pid = state.get('pid')
    started_at = state.get('started_at')
    running = _is_pid_alive(pid)

    if not running and state:
        _clear_state()

    return {
        'running': running,
        'pid': pid if running else None,
        'started_at': started_at if running else None,
    }


def start_crawl_scheduler():
    status = get_crawl_scheduler_status()
    if status['running']:
        return False, f"Crawler scheduler dang chay (PID {status['pid']})."

    cmd = [sys.executable, 'manage.py', 'crawl_winmart', '--schedule']
    kwargs = {
        'cwd': str(BASE_DIR),
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
        'stdin': subprocess.DEVNULL,
    }

    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    try:
        process = subprocess.Popen(cmd, **kwargs)
    except Exception as exc:
        return False, f'Khong the khoi dong crawler scheduler: {exc}'

    _write_state(process.pid)
    return True, f'Da khoi dong crawler scheduler (PID {process.pid}).'


def stop_crawl_scheduler():
    state = _read_state()
    pid = state.get('pid')

    if not pid:
        return False, 'Crawler scheduler hien khong chay.'

    if not _is_pid_alive(pid):
        _clear_state()
        return False, 'Crawler scheduler da dung truoc do.'

    try:
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/PID', str(pid), '/T', '/F'],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception as exc:
        return False, f'Khong the tat crawler scheduler: {exc}'

    _clear_state()
    return True, f'Da gui lenh dung crawler scheduler (PID {pid}).'