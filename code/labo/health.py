"""Etat reel des services, sans confondre les anciennes alertes avec une panne active."""
from pathlib import Path
import shutil
import subprocess
import threading
import time

from .config import DATA

UNITS = ('labo-neurones.service', 'labo-sondes.service', 'labo-web.service', 'ollama.service', 'labo-atelier.service', 'labo-explorations.service')
_lock = threading.Lock()
_cached = None
_at = 0.0
_cpu = {}


def snapshot():
    global _cached, _at, _cpu
    now = time.monotonic()
    with _lock:
        if _cached is not None and now - _at < 5:
            return _cached
        result = {'services': [], 'status': 'unknown'}
        try:
            proc = subprocess.run(['systemctl', 'show', *UNITS, '-p', 'Id', '-p', 'ActiveState',
                                   '-p', 'SubState', '-p', 'NRestarts', '-p', 'CPUUsageNSec'],
                                  capture_output=True, text=True, timeout=3, check=True)
            for block in proc.stdout.strip().split('\n\n'):
                props = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
                name = props.get('Id')
                if name not in UNITS:
                    continue
                raw = props.get('CPUUsageNSec', '')
                cpu = int(raw) if raw.isdigit() else 0
                previous = _cpu.get(name)
                cores = max(0, (cpu - previous) / 1e9 / (now - _at)) if previous is not None and now > _at else None
                _cpu[name] = cpu
                result['services'].append({'name': name.removesuffix('.service'),
                    'state': props.get('ActiveState', 'unknown'), 'detail': props.get('SubState'),
                    'restarts': int(props.get('NRestarts', 0)), 'cpu_cores': round(cores, 2) if cores is not None else None})
            result['status'] = 'ok' if len(result['services']) == len(UNITS) and all(
                s['state'] == 'active' for s in result['services']) else 'degraded'
        except (OSError, ValueError, subprocess.SubprocessError):
            result['status'] = 'unknown'
        try:
            mem = {line.split(':')[0]: int(line.split()[1]) * 1024
                   for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line}
            result['memory'] = {'total': mem['MemTotal'], 'used': mem['MemTotal'] - mem['MemAvailable']}
            disk = shutil.disk_usage(DATA)
            result['disk'] = {'total': disk.total, 'used': disk.used}
        except (OSError, KeyError, ValueError):
            pass
        result['checked_at'] = time.time()
        _cached, _at = result, now
        return result
