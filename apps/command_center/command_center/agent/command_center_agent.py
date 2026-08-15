#!/usr/bin/env python3
"""
Stylo Command Center — server monitoring agent.

Single-file, stdlib-only (deliberately no `psutil`/`requests` — avoids a pip-install
prerequisite on every production server; this script must run with nothing but a
stock Python 3 interpreter). Deployed once to each managed server (e.g. at
/opt/stylo/command_center_agent.py) and run on a cron interval:

    */3 * * * * /usr/bin/python3 /opt/stylo/command_center_agent.py >> /var/log/stylo_agent.log 2>&1

Reads its config from a local JSON file (never re-fetched over the network — the API
key is baked in once at server-onboarding time):

    /opt/stylo/agent_config.json
    {
        "server": "demo",
        "api_key": "<agent_api_key from the Server doctype>",
        "endpoint": "https://command.stylo.io/api/method/command_center.api.metrics.ingest",
        "bench_path": "/home/stylo/stylo"
    }
"""

import json
import os
import shutil
import sys
import urllib.error
import urllib.request

CONFIG_PATH = "/opt/stylo/agent_config.json"

# Non-site entries that live alongside real site directories under <bench>/sites/.
NON_SITE_ENTRIES = {
	"apps.txt",
	"apps.json",
	"common_site_config.json",
	"currentsite.txt",
	"assets",
	".build",
	".migrate",
}


def load_config() -> dict:
	with open(CONFIG_PATH) as f:
		return json.load(f)


def get_load_avg_1m() -> float:
	try:
		with open("/proc/loadavg") as f:
			return float(f.read().split()[0])
	except Exception:
		return 0.0


def get_ram_percent() -> float:
	try:
		meminfo = {}
		with open("/proc/meminfo") as f:
			for line in f:
				key, _, rest = line.partition(":")
				meminfo[key.strip()] = int(rest.strip().split()[0])  # kB
		total = meminfo.get("MemTotal", 0)
		available = meminfo.get("MemAvailable", total)
		if not total:
			return 0.0
		return round((total - available) / total * 100, 2)
	except Exception:
		return 0.0


def get_cpu_percent() -> float:
	"""Cheap single-sample proxy: load_avg_1m relative to CPU core count, capped at 100."""
	try:
		cores = os.cpu_count() or 1
		load = get_load_avg_1m()
		return round(min(load / cores * 100, 100), 2)
	except Exception:
		return 0.0


def get_disk_percent(bench_path: str) -> float:
	try:
		usage = shutil.disk_usage(bench_path)
		return round(usage.used / usage.total * 100, 2)
	except Exception:
		return 0.0


def get_site_count(bench_path: str) -> int:
	try:
		sites_dir = os.path.join(bench_path, "sites")
		entries = os.listdir(sites_dir)
		return sum(
			1
			for e in entries
			if e not in NON_SITE_ENTRIES and os.path.isdir(os.path.join(sites_dir, e))
		)
	except Exception:
		return 0


def main():
	config = load_config()
	bench_path = config["bench_path"]

	payload = {
		"server": config["server"],
		"cpu_percent": get_cpu_percent(),
		"ram_percent": get_ram_percent(),
		"disk_percent": get_disk_percent(bench_path),
		"site_count": get_site_count(bench_path),
		"load_avg_1m": get_load_avg_1m(),
	}

	body = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(
		config["endpoint"],
		data=body,
		method="POST",
		headers={
			"Content-Type": "application/json",
			"X-Agent-Key": config["api_key"],
		},
	)

	try:
		with urllib.request.urlopen(req, timeout=15) as resp:
			resp.read()
			print(f"OK: {payload}")
	except urllib.error.HTTPError as e:
		print(f"FAILED ({e.code}): {e.read().decode(errors='replace')}", file=sys.stderr)
		sys.exit(1)
	except Exception as e:
		print(f"FAILED: {e}", file=sys.stderr)
		sys.exit(1)


if __name__ == "__main__":
	main()
