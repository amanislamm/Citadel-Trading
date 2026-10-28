#!/usr/bin/env python3
"""GAME DAY LAUNCHER:  python3 go.py
Preflight (Python version, full test suite, is RIT running?), then a menu for every tool.
Each tool runs in this terminal; quitting it brings you back to the menu."""
import os, socket, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

MENU = [
    ("1", "Live console (fills, PnL, quotes, all calculators)", ["live.py"], False),
    ("2", "RIT dashboard (read-only, refreshes every second)", ["bots/rit_dash.py"], True),
    ("3", "RIT order console (fast orders, tenders, unwind, hedge)", ["bots/rit_console.py"], True),
    ("4", "RIT connection check", ["bots/run_rit.py", "--check"], True),
    ("5", "RIT bot - PAPER (prints decisions, sends nothing)", ["bots/run_rit.py"], True),
    ("6", "RIT bot - LIVE (sends orders; Ctrl-C cancels all)", ["bots/run_rit.py", "--live"], True),
    ("7", "Valuation template (edit INPUTS in valuation.py first)", ["valuation.py"], False),
    ("8", "Practice drills", ["drill.py"], False),
    ("9", "Practice game (ETF + news)", ["game.py"], False),
    ("f", "Fake RIT server for rehearsal (key KEY, Ctrl-C to stop)", ["sim/fake_rit.py"], False),
    ("p", "Print the scenario playbook", None, False),
    ("c", "Print the cheat sheet", None, False),
    ("t", "Run tests", ["tests/test_all.py"], False),
]

def rit_up(port=None):
    url = os.environ.get("RIT_URL", "http://localhost:9999/v1")
    host = url.split("//")[1].split("/")[0]; h, _, p = host.partition(":")
    try:
        with socket.create_connection((h, int(port or p or 80)), timeout=0.3): return True
    except OSError:
        return False

def preflight(run_tests=True):
    ok = sys.version_info >= (3, 8)
    print(f"Python {sys.version.split()[0]}: {'OK' if ok else 'TOO OLD (need 3.8+)'}")
    if run_tests:
        r = subprocess.run([PY, "tests/test_all.py"], cwd=ROOT, capture_output=True, text=True, timeout=180)
        n = r.stdout.count("PASS")
        print(f"Tests: {n} passed" + ("" if r.returncode == 0 else f", FAILED:\n{r.stderr[-800:]}"))
        ok = ok and r.returncode == 0
    print(f"RIT API at {os.environ.get('RIT_URL', 'localhost:9999')}: {'REACHABLE' if rit_up() else 'not running'}"
          f"   key: {'set' if os.environ.get('RIT_KEY') else 'not set (asked when needed)'}")
    return ok

def main(argv):
    os.chdir(ROOT)
    print("=" * 60 + "\n  CITADEL TRADING CHALLENGE TOOLKIT\n" + "=" * 60)
    preflight(run_tests="--fast" not in argv)
    while True:
        print()
        for k, label, _, _ in MENU: print(f"  {k:>2}  {label}")
        print("   q  quit")
        try: choice = input("go> ").strip().lower()
        except (EOFError, KeyboardInterrupt): print(); return
        if choice in ("q", "quit", "exit"): return
        item = next((m for m in MENU if m[0] == choice), None)
        if not item: continue
        _, label, cmd, needs_key = item
        if choice in ("p", "c"):
            print(open(os.path.join(ROOT, "docs", "PLAYBOOK.md" if choice == "p" else "CHEATSHEET.md")).read()); continue
        if needs_key and not os.environ.get("RIT_KEY"):
            k = input("RIT API key (from the RIT client's API panel): ").strip()
            if not k: continue
            os.environ["RIT_KEY"] = k
        if choice == "6" and input("LIVE trading: type LIVE to confirm: ").strip() != "LIVE": continue
        try: subprocess.call([PY] + cmd, cwd=ROOT)
        except KeyboardInterrupt: pass

if __name__ == "__main__":
    main(sys.argv[1:])
