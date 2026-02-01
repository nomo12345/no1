#!/usr/bin/env python3
"""Migrate data from a local SQLite DB to a PostgreSQL database.

Usage:
  python scripts/migrate_sqlite_to_pg.py --sqlite local.db --target "$DATABASE_URL" [--force]

Notes:
- The script will refuse to write to a non-empty target unless `--force` is provided.
- The script normalizes `postgres://` → `postgresql://` automatically.
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, select, insert
from sqlalchemy.exc import SQLAlchemyError


def normalize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


def parse_args():
    p = argparse.ArgumentParser(description="Migrate local SQLite DB to Postgres (used by this app)")
    p.add_argument('--sqlite', default='local.db', help='Path to sqlite DB file (default: local.db)')
    p.add_argument('--target', default=os.environ.get('DATABASE_URL'), help='Target Postgres DATABASE_URL')
    p.add_argument('--force', action='store_true', help='Overwrite target tables if not empty')
    return p.parse_args()


def main():
    args = parse_args()

    if not args.target:
        print('ERROR: Target DATABASE_URL is required (use --target or set DATABASE_URL env var)')
        sys.exit(2)

    target = normalize_db_url(args.target)

    sqlite_path = args.sqlite
    if not os.path.exists(sqlite_path):
        print(f'ERROR: sqlite file not found: {sqlite_path}')
        sys.exit(2)

    # Define table schemas (matching app models)
    metadata = MetaData()
    complaint = Table('complaint', metadata,
                      Column('id', Integer, primary_key=True),
                      Column('name', String(100)),
                      Column('content', Text),
                      Column('date_posted', DateTime))

    admin = Table('admin', metadata,
                  Column('id', Integer, primary_key=True),
                  Column('password_hash', String(255), nullable=False))

    try:
        pg_engine = create_engine(target)
        # Create tables on target if they don't exist
        metadata.create_all(pg_engine)
    except SQLAlchemyError as e:
        print('ERROR connecting to target DB:', e)
        sys.exit(1)

    with pg_engine.connect() as pg_conn:
        # check if target tables have data
        complaint_count = pg_conn.execute(select(complaint.count())).scalar()
        admin_count = pg_conn.execute(select(admin.count())).scalar()

        if (complaint_count or admin_count) and not args.force:
            print('Target database already has data. Use --force to overwrite. Aborting.')
            print(f'complaint rows: {complaint_count}, admin rows: {admin_count}')
            sys.exit(3)

        if args.force:
            print('Clearing target tables (force mode)')
            pg_conn.execute(complaint.delete())
            pg_conn.execute(admin.delete())

        # Read from sqlite
        sconn = sqlite3.connect(sqlite_path)
        sconn.row_factory = sqlite3.Row
        cur = sconn.cursor()

        # Migrate complaints
        cur.execute('SELECT id, name, content, date_posted FROM complaint')
        complaints = cur.fetchall()
        print(f'Found {len(complaints)} complaint(s) in sqlite')

        for row in complaints:
            params = {
                'id': row['id'],
                'name': row['name'],
                'content': row['content'],
                'date_posted': None
            }
            try:
                dp = row['date_posted']
                # sqlite may store datetime as string or timestamp
                if isinstance(dp, (int, float)):
                    params['date_posted'] = datetime.fromtimestamp(dp)
                elif isinstance(dp, str) and dp.strip():
                    try:
                        # Try parsing ISO format
                        params['date_posted'] = datetime.fromisoformat(dp)
                    except Exception:
                        params['date_posted'] = dp  # let SQLAlchemy try
                else:
                    params['date_posted'] = None
            except Exception:
                params['date_posted'] = None

            pg_conn.execute(insert(complaint).values(**params))

        # Migrate admin (only first row expected)
        cur.execute('SELECT id, password_hash FROM admin')
        admins = cur.fetchall()
        print(f'Found {len(admins)} admin row(s) in sqlite')
        for row in admins:
            params = {'id': row['id'], 'password_hash': row['password_hash']}
            pg_conn.execute(insert(admin).values(**params))

        sconn.close()

    print('\nMigration completed successfully.')


if __name__ == '__main__':
    main()
