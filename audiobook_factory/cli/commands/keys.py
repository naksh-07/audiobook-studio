#!/usr/bin/env python3
"""
Audiobook Factory - CLI Commands: Key Inventory & Lease Fleet Monitor.
======================================================================
Provides terminal visibility into:
1. Active keys, daily quota consumption, and backoff states.
2. Active multi-user leases and process locks.
3. Security audit log (zero secrets exposed).
"""

from __future__ import annotations
import sys
from typing import Any

from audiobook_factory.core.models import (
    get_key_lease_manager,
    get_db_connection,
    DEFAULT_DB_PATH,
)


def cmd_keys(args: Any) -> None:
    """Dispatches 'keys status' or 'keys audit' subcommand."""
    action = getattr(args, "keys_action", "status")
    if action == "status":
        cmd_keys_status(args)
    elif action == "audit":
        cmd_keys_audit(args)
    elif action == "reset":
        cmd_keys_reset(args)
    else:
        cmd_keys_status(args)


def cmd_keys_status(args: Any) -> None:
    """Displays live key inventory, quota health, and active leases."""
    provider = getattr(args, "provider", "gemini") or "gemini"
    mgr = get_key_lease_manager()
    summary = mgr.get_status_summary(provider=provider)

    print("\n" + "=" * 70)
    print(f"  AUDIOBOOK FACTORY - KEY INVENTORY & FLEET STATUS ({provider.upper()})")
    print("=" * 70)
    print(f"  Date (Quota Period)   : {summary['date']}")
    print(f"  Total Registered Keys : {summary['total_keys']}")
    print(f"  Active Healthy Keys   : {summary['active_keys']}")
    print(f"  Exhausted Today       : {summary['exhausted_today']}")
    print(f"  Temporary Backoff     : {summary['temp_backoff']}")
    print(f"  In-Flight Leases      : {summary['active_leases_count']}")
    print("-" * 70)

    # Active Leases Table
    if summary["active_leases"]:
        print("\n  ACTIVE LEASES (IN-FLIGHT CONCURRENCY):")
        print(f"  {'LEASE ID':<20} {'ALIAS':<12} {'USER':<14} {'WORKLOAD':<10} {'EXPIRES'}")
        print("  " + "-" * 66)
        for l in summary["active_leases"]:
            print(f"  {l['lease_id']:<20} {l.get('key_alias', 'N/A'):<12} {l['user_id']:<14} {l['workload_type']:<10} {l['expires_at']}")
    else:
        print("\n  ACTIVE LEASES: None (Fleet is idle).")

    # Registered Keys Inventory Table
    print("\n  KEY INVENTORY DETAILS:")
    print(f"  {'ALIAS':<14} {'STATUS':<16} {'CALLS TODAY':<14} {'LAST USED'}")
    print("  " + "-" * 66)
    for k in summary["keys"]:
        last_u = str(k.get("last_used") or "Never")[:19]
        calls = f"{k.get('success_calls_today', 0)} ok / {k.get('failed_calls_today', 0)} fail"
        print(f"  {k['key_alias']:<14} {k['status']:<16} {calls:<14} {last_u}")

    print("=" * 70 + "\n")


def cmd_keys_audit(args: Any) -> None:
    """Displays recent tamper-evident lease audit log."""
    limit = getattr(args, "limit", 25) or 25
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT event_type, lease_id, key_alias, user_id, process_id, model_id,
                   provider, timestamp, error_summary
            FROM key_audit_log
            ORDER BY timestamp DESC
            LIMIT ?;
        """, (limit,)).fetchall()

    print("\n" + "=" * 70)
    print(f"  AUDIOBOOK FACTORY - KEY LEASE AUDIT LOG (LAST {limit} EVENTS)")
    print("=" * 70)
    if not rows:
        print("  No audit events recorded yet.")
    else:
        print(f"  {'TIMESTAMP':<19} {'EVENT':<8} {'ALIAS':<12} {'USER':<14} {'MODEL'}")
        print("  " + "-" * 66)
        for r in rows:
            ts = str(r["timestamp"])[:19]
            ev = r["event_type"]
            ka = r["key_alias"] or "N/A"
            usr = r["user_id"] or "N/A"
            mdl = r["model_id"] or "-"
            print(f"  {ts:<19} {ev:<8} {ka:<12} {usr:<14} {mdl}")

    print("=" * 70 + "\n")



def cmd_keys_reset(args: Any) -> None:
    """Forces administrative reset of all keys back to ACTIVE state."""
    mgr = get_key_lease_manager()
    mgr.reset_all_for_today()
    print("\n[+] Success: All keys and model quota ledgers reset to ACTIVE state for today.\n")
