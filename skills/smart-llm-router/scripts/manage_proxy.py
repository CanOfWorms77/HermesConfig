#!/usr/bin/env python3
"""
Manage the Smart LLM Router Proxy process.

Usage:
    python scripts/manage_proxy.py start      # start proxy in background
    python scripts/manage_proxy.py stop       # stop proxy
    python scripts/manage_proxy.py status     # show status
    python scripts/manage_proxy.py restart    # restart proxy
    python scripts/manage_proxy.py logs       # tail logs
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PIDFILE = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "proxy.pid"
LOGFILE = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "proxy.log"
PROXY_SCRIPT = Path(__file__).with_name("router_proxy.py")
ENV_PATH = Path.home() / ".hermes" / ".env"


def load_dotenv(path: Path) -> dict:
    """Load KEY=VALUE lines from a .env file into a dict."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_pid() -> int:
    if PIDFILE.exists():
        try:
            return int(PIDFILE.read_text().strip())
        except Exception:
            pass
    return None


def is_running(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cmd_start(args):
    pid = get_pid()
    if pid and is_running(pid):
        print(f"Proxy already running (pid {pid})")
        return

    # Merge .env into subprocess environment so API keys are available
    env = os.environ.copy()
    env.update(load_dotenv(ENV_PATH))

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOGFILE, "a") as logf:
        proc = subprocess.Popen(
            [sys.executable, str(PROXY_SCRIPT), "--config", str(args.config)],
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
    PIDFILE.write_text(str(proc.pid))
    time.sleep(1)
    if is_running(proc.pid):
        print(f"Proxy started (pid {proc.pid})  http://localhost:{args.port}")
    else:
        print("Proxy failed to start. Check logs:")
        print(f"  tail -f {LOGFILE}")
        sys.exit(1)


def cmd_stop(args):
    pid = get_pid()
    if not pid or not is_running(pid):
        print("Proxy not running")
        PIDFILE.unlink(missing_ok=True)
        return
    os.kill(pid, signal.SIGTERM)
    for _ in range(10):
        if not is_running(pid):
            break
        time.sleep(0.5)
    if is_running(pid):
        os.kill(pid, signal.SIGKILL)
    PIDFILE.unlink(missing_ok=True)
    print("Proxy stopped")


def cmd_status(args):
    pid = get_pid()
    if pid and is_running(pid):
        print(f"Proxy running (pid {pid})")
        # Try health endpoint
        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:8765/health", timeout=2) as r:
                data = json.loads(r.read())
                print(f"Health: {data}")
        except Exception as e:
            print(f"Health check failed: {e}")
    else:
        print("Proxy not running")


def cmd_restart(args):
    cmd_stop(args)
    time.sleep(1)
    cmd_start(args)


def cmd_logs(args):
    if not LOGFILE.exists():
        print("No log file yet")
        return
    n = args.lines if hasattr(args, "lines") else 50
    subprocess.run(["tail", f"-{n}", str(LOGFILE)])


def main():
    parser = argparse.ArgumentParser(description="Manage LLM Router Proxy")
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "logs", "discover"])
    parser.add_argument("--config", type=Path,
                        default=Path.home() / ".hermes" / "skills" / "smart-llm-router" / "config.yaml")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--lines", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true", help="For discover: test only, don't write config")
    parser.add_argument("--tier", default="all", help="For discover: which tier to probe")
    parser.add_argument("--providers", default="openrouter,groq,nvidia", help="For discover: comma-separated providers")
    args = parser.parse_args()

    if args.action == "discover":
        discover_script = Path(__file__).with_name("discover_models.py")
        cmd = [
            sys.executable, str(discover_script),
            "--config", str(args.config),
            "--tier", args.tier,
            "--providers", args.providers,
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        os.execv(sys.executable, cmd)

    globals()[f"cmd_{args.action}"](args)


if __name__ == "__main__":
    main()
