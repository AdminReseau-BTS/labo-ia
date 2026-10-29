import sqlite3
import time


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    # WAL : le tableau de bord peut lire pendant que la mission ecrit.
    con.execute("PRAGMA journal_mode=WAL")
    return con


def journal(con, log, msg):
    log.info(msg)
    con.execute("INSERT INTO journal VALUES (?, ?)", (time.time(), msg))
    con.commit()


def rows(path, sql, args=()):
    """Lecture tolerante : avant le premier passage d'une mission, sa base n'existe pas encore."""
    if not path.exists():
        return []
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def scalar(path, sql, args=()):
    r = rows(path, sql, args)
    return (r[0][0] if r else None) or 0
