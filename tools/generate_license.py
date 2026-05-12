#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# tools/generate_license.py
#
# INTERNAL USE ONLY — never ship this tool to clients.
#
# Generates HMAC-SHA256 license keys for Styloworld client deployments.
# The key format matches what stylo_core/license.py validates on every request.
#
# Usage:
#   STYLO_BUILD_SECRET=<your-secret> python tools/generate_license.py \
#       <domain> <expiry-YYYY-MM-DD>
#
# Examples:
#   python tools/generate_license.py client.com 2027-01-01
#   python tools/generate_license.py *.client.com 2027-06-30   # wildcard
#
# Output format:
#   {domain}:{YYYY-MM-DD}:{hmac-sha256-signature}
#
# The client copies the key into their .env as STYLO_LICENSE_KEY=...
# The Docker image validates it using the same STYLO_BUILD_SECRET baked
# in at build time via --build-arg STYLO_BUILD_SECRET=<secret>.
# ─────────────────────────────────────────────────────────────────────────────
"""
Styloworld License Key Generator — INTERNAL USE ONLY. Never ship to clients.

Usage:
  python tools/generate_license.py <domain> <expiry-YYYY-MM-DD>

Example:
  python tools/generate_license.py client.com 2027-01-01
  python tools/generate_license.py *.client.com 2027-06-30

The STYLO_BUILD_SECRET env var must match what was used when building the Docker image.

Output:
  A license key string in the format: {domain}:{expiry}:{hmac}
  Client sets this as STYLO_LICENSE_KEY in their .env file.
"""

import hashlib
import hmac
import os
import sys
from datetime import date, datetime


def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/generate_license.py <domain> <YYYY-MM-DD>")
        print("Example: python tools/generate_license.py client.com 2027-01-01")
        sys.exit(1)

    secret = os.environ.get("STYLO_BUILD_SECRET", "")
    if not secret:
        print("ERROR: STYLO_BUILD_SECRET env var not set.")
        print("Set it to the same secret used when building the Docker image.")
        sys.exit(1)

    domain = sys.argv[1]
    expiry_str = sys.argv[2]

    # Validate expiry date
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"ERROR: Invalid date format '{expiry_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

    if expiry < date.today():
        print(f"WARNING: Expiry date {expiry_str} is in the past.")

    # Generate HMAC signature
    message = f"{domain}:{expiry_str}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    key = f"{domain}:{expiry_str}:{signature}"

    print(f"\nLicense key for '{domain}' (expires {expiry_str}):")
    print(f"\n  {key}\n")
    print("Add to client's .env file:")
    print(f"  STYLO_LICENSE_KEY={key}")


if __name__ == "__main__":
    main()
