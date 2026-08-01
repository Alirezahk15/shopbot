#!/usr/bin/env python3
"""Offline recovery tool for the ShopBot admin panel.

Use this when you are completely locked out of the panel: it sets a panel
username and password directly in the database, without needing the bot,
Telegram, or the old password.

Usage (on the server):
    cd /opt/shopbot
    sudo -u shopbot venv/bin/python reset_panel_admin.py
    sudo -u shopbot venv/bin/python reset_panel_admin.py --username admin --password 'NewPass123'
    sudo -u shopbot venv/bin/python reset_panel_admin.py --list

All messages are English on purpose: terminals cannot render Persian reliably.
"""
import argparse
import getpass
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def fail(msg, *hints):
    print("\n[ERROR] " + msg)
    if hints:
        print("\nHow to fix this:")
        for i, h in enumerate(hints, 1):
            print("  %d. %s" % (i, h))
    sys.exit(1)


try:
    import database as db
except Exception as exc:
    fail(
        "Could not import database.py (%s)" % exc,
        "Run this from the install directory: cd /opt/shopbot",
        "Use the virtualenv interpreter: venv/bin/python reset_panel_admin.py",
    )

try:
    import bcrypt
except Exception:
    fail(
        "The 'bcrypt' package is not available.",
        "Use the project virtualenv: sudo -u shopbot venv/bin/python reset_panel_admin.py",
        "Or install it: sudo -u shopbot venv/bin/pip install bcrypt",
    )


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode("utf-8")


def list_admins():
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT user_id, panel_username, is_super, permissions, "
            "       (panel_password_hash IS NOT NULL AND panel_password_hash<>'') AS has_pw, "
            "       COALESCE(totp_enabled,0) AS totp "
            "FROM admins ORDER BY is_super DESC, user_id"
        ).fetchall()
    if not rows:
        print("\nNo admins found in the database yet.")
        print("Send /start to your bot once as the owner, then run this again.")
        return rows
    print("\n%-14s %-16s %-7s %-10s %s" % ("USER_ID", "USERNAME", "SUPER", "PASSWORD", "2FA"))
    print("-" * 60)
    for r in rows:
        print("%-14s %-16s %-7s %-10s %s" % (
            r["user_id"],
            r["panel_username"] or "(none)",
            "yes" if r["is_super"] else "no",
            "set" if r["has_pw"] else "(none)",
            "on" if r["totp"] else "off",
        ))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Reset a ShopBot panel admin login.")
    ap.add_argument("--user-id", type=int, help="Telegram numeric ID of the admin")
    ap.add_argument("--username", help="Panel login username to set")
    ap.add_argument("--password", help="New panel password (omit to be prompted)")
    ap.add_argument("--disable-2fa", action="store_true", help="Also turn off two-factor auth")
    ap.add_argument("--list", action="store_true", help="List existing admins and exit")
    args = ap.parse_args()

    db.init_db()

    if args.list:
        list_admins()
        return

    print("=" * 60)
    print(" ShopBot - panel admin recovery")
    print("=" * 60)
    rows = list_admins()

    user_id = args.user_id
    if user_id is None:
        if len(rows) == 1:
            user_id = rows[0]["user_id"]
            print("\nUsing the only admin found: %s" % user_id)
        else:
            try:
                raw = input("\nTelegram user ID to reset: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(1)
            if not raw.isdigit():
                fail("That is not a numeric Telegram ID.",
                     "Find your ID by sending /start to your bot.",
                     "Or message @userinfobot on Telegram to get it.")
            user_id = int(raw)

    username = args.username
    if not username:
        try:
            username = input("Panel username [admin]: ").strip() or "admin"
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(1)

    password = args.password
    if not password:
        try:
            password = getpass.getpass("New password (min 6 chars): ")
            confirm = getpass.getpass("Confirm password: ")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(1)
        if password != confirm:
            fail("The two passwords do not match.", "Run the tool again and retype them carefully.")

    if len(password) < 6:
        fail("Password must be at least 6 characters.")

    with db.get_db() as conn:
        clash = conn.execute(
            "SELECT user_id FROM admins WHERE lower(panel_username)=lower(?) AND user_id<>?",
            (username, user_id),
        ).fetchone()
        if clash:
            fail("Username '%s' already belongs to admin %s." % (username, clash["user_id"]),
                 "Pick a different username with --username",
                 "Or reset that admin instead: --user-id %s" % clash["user_id"])

        exists = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO admins (user_id, is_super, permissions) VALUES (?,1,'all')",
                (user_id,),
            )
            print("\nCreated a new super-admin row for %s." % user_id)

        if args.disable_2fa:
            conn.execute(
                "UPDATE admins SET panel_username=?, panel_password_hash=?, is_super=1, "
                "permissions='all', reset_code_hash='', reset_code_expires='', "
                "totp_enabled=0, totp_secret='', totp_pending_secret='' WHERE user_id=?",
                (username, hash_password(password), user_id),
            )
        else:
            conn.execute(
                "UPDATE admins SET panel_username=?, panel_password_hash=?, is_super=1, "
                "permissions='all', reset_code_hash='', reset_code_expires='' WHERE user_id=?",
                (username, hash_password(password), user_id),
            )

    print("\n" + "=" * 60)
    print(" DONE - you can now sign in to the panel")
    print("=" * 60)
    print("  Username : %s" % username)
    print("  Password : (the one you just set)")
    if args.disable_2fa:
        print("  Two-factor authentication was turned OFF.")
    print("\nIf the panel still rejects it, restart the services:")
    print("  sudo systemctl restart shopbot-panel shopbot")


if __name__ == "__main__":
    main()
