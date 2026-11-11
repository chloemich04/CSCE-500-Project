"""pg_stat_statements helper (step 1: are writes the bottleneck?).
    python M6/pgss.py reset            # on every DB used by the test
    python M6/pgss.py top <label>      # top statements by total_exec_time -> M6/results/<label>_pgss.txt
"""
import sys
from pathlib import Path
import psycopg2
from dotenv import dotenv_values

ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
DBS = {"shard_0 / single (us-west-2)": ENV["DATABASE_URL"], "shard_1 (us-east-1)": ENV["SHARD_1_URL"]}

TOP = r"""
SELECT calls, round(total_exec_time::numeric, 0) AS total_ms, round(mean_exec_time::numeric, 2) AS mean_ms,
       rows, left(regexp_replace(query, '\s+', ' ', 'g'), 90) AS query
FROM extensions.pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query !~* '^(SET|SHOW|BEGIN|COMMIT|ROLLBACK|select 1)'
  AND query !~* 'pg_stat_statements|pg_catalog|pg_database|pg_settings'
ORDER BY total_exec_time DESC LIMIT 10"""

def main(cmd, label=""):
    out = []
    for name, url in DBS.items():
        c = psycopg2.connect(url); c.autocommit = True; cur = c.cursor()
        if cmd == "reset":
            cur.execute("SELECT extensions.pg_stat_statements_reset()")
        else:
            cur.execute(TOP)
            out.append(f"=== {name}\n{'calls':>7} {'total_ms':>9} {'mean_ms':>8} {'rows':>7}  query")
            for calls, tot, mean, rows, q in cur.fetchall():
                out.append(f"{calls:>7} {tot:>9} {mean:>8} {rows:>7}  {q}")
        c.close()
    if out:
        text = "\n".join(out)
        print(text)
        (Path(__file__).resolve().parent / "results" / f"{label}_pgss.txt").write_text(text, encoding="utf-8")

main(*sys.argv[1:])
