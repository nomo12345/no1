#!/usr/bin/env python3
"""Set or update the admin password for the app.

Usage:
  # Set password interactively (default uses local DB or DATABASE_URL env)
  python scripts/set_admin_password.py

  # Provide password via CLI (safer than committing to repo)
  python scripts/set_admin_password.py --password "newSecret123"

  # Target a remote DB using a DATABASE_URL
  python scripts/set_admin_password.py --password "newSecret123" --target "postgres://user:pw@host:5432/db"

Notes:
- The script will normalize `postgres://` -> `postgresql://` before connecting.
"""

import os
import sys
import argparse
import getpass


def normalize_db_url(url: str) -> str:
    if not url:
        return url
    return url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url


def parse_args():
    p = argparse.ArgumentParser(description='Set admin password for the app (updates DB).')
    p.add_argument('--password', '-p', help='The new admin password (use interactive prompt if omitted)')
    p.add_argument('--target', '-t', help='Optional DATABASE_URL to target (overrides env var)')
    return p.parse_args()


def main():
    args = parse_args()

    pwd = args.password
    if not pwd:
        try:
            pwd = getpass.getpass('New admin password: ')
        except Exception:
            print('\nFailed to read password interactively. Use --password to pass it as an argument.')
            sys.exit(2)

    if not pwd or len(pwd) < 4:
        print('Password must be at least 4 characters long (choose a stronger password for production).')
        sys.exit(2)

    # If target provided, set DATABASE_URL in env for this process
    if args.target:
        dburl = normalize_db_url(args.target)
        os.environ['DATABASE_URL'] = dburl

    # Import app and set password
    try:
        # Import here so environment overrides apply before SQLAlchemy is configured
        from papa import app, set_admin_password
    except Exception as e:
        print('ERROR importing application:', e)
        sys.exit(1)

    with app.app_context():
        try:
            set_admin_password(pwd)
            print('Admin password set successfully.')
        except Exception as e:
            print('ERROR setting admin password:', e)
            sys.exit(1)


if __name__ == '__main__':
    main()
