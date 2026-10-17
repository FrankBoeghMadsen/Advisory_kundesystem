from db import execute, fetch_df


def q(sql, params=()):
    return fetch_df(sql, params)


def run(sql, params=()):
    execute(sql, params)


def count_for(table, company_id):
    try:
        return int(q(f"SELECT COUNT(*) AS n FROM {table} WHERE company_id=?", (company_id,))["n"].iloc[0])
    except Exception:
        return 0


def latest_meeting_id(company_id):
    df = q(
        "SELECT id FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC LIMIT 1",
        (company_id,),
    )
    if len(df):
        return int(df["id"].iloc[0])
    return None
