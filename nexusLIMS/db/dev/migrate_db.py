#!/usr/bin/env python
"""
A standalone script to migrate a NexusLIMS sqlite database to a new schema.

Schema is defined in the `$DB_CREATION_SCRIPT` file. All entries in the
``session_log`` table of the database specified by ``old_db`` will be
recreated in the same table in ``new_db``.

Because the `$DB_CREATION_SCRIPT` file requires access to a file named
`$DB_NAME`, if that file exists in the current directory, no action will be
performed to prevent clobbering an existing database.
"""
# ruff: noqa: T201, INP001, SIM117
#
#  NIST Public License - 2020
#
#  This software was developed by employees of the National Institute of
#  Standards and Technology (NIST), an agency of the Federal Government
#  and is being made available as a public service. Pursuant to title 17
#  United States Code Section 105, works of NIST employees are not subject
#  to copyright protection in the United States.  This software may be
#  subject to foreign copyright.  Permission in the United States and in
#  foreign countries, to the extent that NIST may hold copyright, to use,
#  copy, modify, create derivative works, and distribute this software and
#  its documentation without fee is hereby granted on a non-exclusive basis,
#  provided that this notice and disclaimer of warranty appears in all copies.
#
#  THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
#  EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
#  TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
#  IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
#  AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION
#  WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE
#  ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING,
#  BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES,
#  ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE,
#  WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER
#  OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND
#  WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF,
#  OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.
#
# ruff: noqa: A001
import argparse
import contextlib
import shutil
import sqlite3
import sys
from pathlib import Path

db_creation_script = Path(__file__).parent / "NexusLIMS_db_creation_script.sql"
DB_NAME = Path("nexuslims_db.sqlite")
__doc__ = __doc__.replace("$DB_CREATION_SCRIPT", db_creation_script.name)
__doc__ = __doc__.replace("$DB_NAME", DB_NAME.name)


def main(arguments):
    """
    Run the migration.

    Parameters
    ----------
    old_db : str
        Input (old) database from which ``session_log`` records will be copied
    new_db : str
        Output database (path to file will be created if it does not exist) to
        which ``session_log`` records will be copied
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "old_db",
        help="Input (old) database from which session_log records will be copied",
    )
    parser.add_argument(
        "new_db",
        help="Output database (path to file will be "
        "created if it does not exist) to "
        "which session_log records will be "
        "copied",
    )

    args = parser.parse_args(arguments)
    in_path = Path(args.old_db)

    out_path = Path(args.new_db)
    out_dir = out_path.parent
    out_fname = out_path.name
    print("")

    if DB_NAME.is_file():
        return (
            f"ERROR: A {DB_NAME} file already exists in this folder. "
            f"The migration requires this file be created during the "
            f"process, so no "
            f"actions were performed to prevent clobbering the database. "
            f"Please run this script from a folder that does not contain a"
            f" file named {DB_NAME}."
        )

    if out_path.is_file():
        return (
            f"ERROR: A {out_fname} file already exists in the output "
            f"folder. No actions were performed to prevent clobbering that"
            f" database. Please rerun this script with a different "
            f'"new_db" parameter.'
        )

    if not db_creation_script.is_file():
        return (
            f"ERROR: Could not find the database creation script at "
            f"{db_creation_script}. Please check for the file and try again."
        )

    if not out_dir.is_dir():
        print(f"Created new directory for output: {out_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Executing {db_creation_script}...")
    with db_creation_script.open(encoding="utf-8") as sql_file:
        sql_script = sql_file.read()
    with contextlib.closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                cursor.executescript(sql_script)

    print(
        f"Renaming {DB_NAME} to {out_fname} and moving to {out_dir}...",
    )
    shutil.move(DB_NAME, out_path)

    print(f"Copying session_log entries from {in_path} to {out_path}")
    migration_commands = [
        f"ATTACH database '{in_path}' as db_old;",
        "INSERT INTO session_log SELECT * FROM db_old.session_log;",
    ]
    with contextlib.closing(sqlite3.connect(out_path)) as conn:
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                for cmd in migration_commands:
                    cursor.execute(cmd)

    print("Checking to make sure number of session logs match...")
    with contextlib.closing(sqlite3.connect(out_path)) as conn:
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                cursor.execute("SELECT COUNT(session_identifier) FROM session_log;")
                new_session_count = cursor.fetchone()[0]
    with contextlib.closing(sqlite3.connect(in_path)) as conn:
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                cursor.execute("SELECT COUNT(session_identifier) FROM session_log;")
                old_session_count = cursor.fetchone()[0]
    print(f"{in_path.name()}: {old_session_count}")
    print(f"{out_path.name()}: {new_session_count}")
    if new_session_count != old_session_count:
        msg = "New session count did not match old session count"
        raise AssertionError(msg)
    return "Looks good!"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
