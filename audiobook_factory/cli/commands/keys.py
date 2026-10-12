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
    get_key_quarantine_manager,
    get_db_connection,
    DEFAULT_DB_PATH,
)


def cmd_keys(args: Any) -> None:
    """Dispatches 'keys' subcommands: status, list, add, sweep, test, audit, reset, quarantine."""
    action = getattr(args, "keys_action", "status")
    if action == "status":
        cmd_keys_status(args)
    elif action == "list":
        cmd_keys_list(args)
    elif action == "add":
        cmd_keys_add(args)
    elif action == "sweep":
        cmd_keys_sweep(args)
    elif action == "test":
        cmd_keys_test(args)
    elif action == "audit":
        cmd_keys_audit(args)
    elif action == "reset":
        cmd_keys_reset(args)
    elif action == "quarantine":
        cmd_keys_quarantine(args)
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


def cmd_keys_list(args: Any) -> None:
    """Lists registered keys with their safe public aliases and operational states."""
    provider = getattr(args, "provider", "gemini") or "gemini"
    mgr = get_key_lease_manager()
    summary = mgr.get_status_summary(provider=provider)

    print("\n" + "=" * 70)
    print(f"  AUDIOBOOK FACTORY - REGISTERED KEY INVENTORY ({provider.upper()})")
    print("=" * 70)
    print(f"  {'ALIAS':<14} {'STATUS':<16} {'CALLS TODAY':<14} {'LAST USED'}")
    print("  " + "-" * 66)
    for k in summary["keys"]:
        last_u = str(k.get("last_used") or "Never")[:19]
        calls = f"{k.get('success_calls_today', 0)} ok / {k.get('failed_calls_today', 0)} fail"
        print(f"  {k['key_alias']:<14} {k['status']:<16} {calls:<14} {last_u}")
    print("=" * 70 + "\n")


def cmd_keys_add(args: Any) -> None:
    """Registers an API key into the ACID key inventory ledger."""
    provider = getattr(args, "provider", "gemini") or "gemini"
    key = getattr(args, "key", None)
    if not key:
        print("[!] Error: Specify API key to add via --key <KEY>", file=sys.stderr)
        return
    mgr = get_key_lease_manager()
    mgr.register_keys([key], provider=provider)
    print(f"\n[+] Success: Key registered in inventory ledger under provider '{provider}'.\n")


def cmd_keys_sweep(args: Any) -> None:
    """Reclaims stale expired TTL leases and orphaned dead-PID process locks."""
    mgr = get_key_lease_manager()
    with get_db_connection() as conn:
        reclaimed = mgr.sweep_stale_and_dead_leases(conn)
    print(f"\n[+] Sweep complete: Reclaimed {reclaimed} stale or dead-PID lease(s).\n")


def cmd_keys_test(args: Any) -> None:
    """Probes key fleet availability and health status."""
    provider = getattr(args, "provider", "gemini") or "gemini"
    mgr = get_key_lease_manager()
    summary = mgr.get_status_summary(provider=provider)
    active = summary.get("active_keys", 0)
    total = summary.get("total_keys", 0)
    print("\n" + "=" * 70)
    print(f"  AUDIOBOOK FACTORY - KEY FLEET HEALTH PROBE ({provider.upper()})")
    print("=" * 70)
    print(f"  Total Keys   : {total}")
    print(f"  Active Keys  : {active}")
    print(f"  Exhausted    : {summary.get('exhausted_today', 0)}")
    print(f"  Backoff      : {summary.get('temp_backoff', 0)}")
    if active > 0:
        print(f"  Probe Status : HEALTHY ({active}/{total} keys available for traffic)")
    else:
        print(f"  Probe Status : DEGRADED (0 active keys available)")
    print("=" * 70 + "\n")


def cmd_keys_quarantine(args: Any) -> None:
    """Manages the quarantine vault for permanently blocked, revoked, or suspended keys."""
    subaction = getattr(args, "quarantine_action", "list") or "list"
    q_mgr = get_key_quarantine_manager()
    provider = getattr(args, "provider", None)

    if subaction == "list":
        records = q_mgr.list_quarantined(provider=provider)
        print("\n" + "=" * 76)
        print("  AUDIOBOOK FACTORY - KEY QUARANTINE VAULT (PERMANENT ISOLATION)")
        print("=" * 76)
        print(f"  Total Quarantined Keys : {len(records)}")
        print("  Status                 : ISOLATED (Physically excluded from active inventory)")
        print("-" * 76)
        if not records:
            print("  No quarantined keys in vault. All keys are healthy or in standard inventory.")
        else:
            print(f"  {'ALIAS':<14} {'PROVIDER':<10} {'CODE':<6} {'REASON':<24} {'DATE QUARANTINED'}")
            print("  " + "-" * 72)
            for r in records:
                q_date = str(r.quarantined_at)[:16]
                reason = r.quarantine_reason[:23]
                print(f"  {r.key_alias:<14} {r.provider:<10} {r.error_code:<6} {reason:<24} {q_date}")
            print("-" * 76)
            print("  Commands:")
            print("    Inspect : python audiobook_cli.py keys quarantine inspect --alias <ALIAS>")
            print("    Purge   : python audiobook_cli.py keys quarantine purge --alias <ALIAS> [--all]")
            print("    Export  : python audiobook_cli.py keys quarantine export --out ./quarantined.json")
            print("    Restore : python audiobook_cli.py keys quarantine restore --alias <ALIAS>")
        print("=" * 76 + "\n")

    elif subaction == "inspect":
        alias = getattr(args, "alias", None)
        if not alias:
            print("[!] Error: Specify key alias to inspect via --alias <ALIAS>", file=sys.stderr)
            return
        rec = q_mgr.get_quarantined(alias)
        if not rec:
            print(f"[!] Error: Key '{alias}' not found in quarantine vault.", file=sys.stderr)
            return
        print("\n" + "=" * 70)
        print(f"  QUARANTINE RECORD: {rec.key_alias}")
        print("=" * 70)
        print(f"  Key Hash         : {rec.key_hash}")
        print(f"  Provider         : {rec.provider}")
        print(f"  HTTP Error Code  : {rec.error_code}")
        print(f"  Quarantine Reason: {rec.quarantine_reason}")
        print(f"  Quarantined By   : {rec.quarantined_by}")
        print(f"  Quarantined At   : {rec.quarantined_at}")
        print(f"  Permanent Block  : {'YES' if rec.is_permanent else 'NO'}")
        if rec.error_body_snippet:
            print("-" * 70)
            print("  Error Snippet:")
            print(f"  {rec.error_body_snippet}")
        print("=" * 70 + "\n")

    elif subaction == "purge":
        purge_all = getattr(args, "purge_all", False)
        alias = getattr(args, "alias", None)
        if not purge_all and not alias:
            print("[!] Error: Specify --alias <ALIAS> or --all to permanently purge keys.", file=sys.stderr)
            return
        targets = [alias] if alias else None
        reaped = q_mgr.purge_keys(key_aliases_or_hashes=targets, purge_all=purge_all, provider=provider)
        print(f"\n[+] Success: Permanently purged {reaped} key(s) from quarantine vault.\n")

    elif subaction == "export":
        out_path = getattr(args, "out", None) or "quarantined_keys.json"
        include_keys = getattr(args, "include_keys", False)
        from pathlib import Path
        count = q_mgr.export_quarantined(Path(out_path), include_plaintext=include_keys)
        print(f"\n[+] Success: Exported {count} quarantined key records to '{out_path}'.\n")

    elif subaction == "restore":
        alias = getattr(args, "alias", None)
        if not alias:
            print("[!] Error: Specify key alias to restore via --alias <ALIAS>", file=sys.stderr)
            return
        ok = q_mgr.restore_key(alias)
        if ok:
            print(f"\n[+] Success: Key '{alias}' restored to active inventory ledger.\n")
        else:
            print(f"\n[!] Error: Key '{alias}' not found in quarantine vault.\n", file=sys.stderr)

    else:
        print(f"[!] Unknown quarantine action '{subaction}'. Choices: list, inspect, purge, export, restore", file=sys.stderr)

