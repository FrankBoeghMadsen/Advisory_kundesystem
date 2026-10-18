"""Optional track links reuse the existing single-track relationship."""
from repositories import q


def tracks_for_company(company_id):
    return q('SELECT id,title FROM commercial_tracks WHERE company_id=? ORDER BY title', (company_id,))


def validate_track(company_id, track_id):
    if track_id is not None:
        rows = tracks_for_company(company_id)
        if track_id not in rows['id'].tolist():
            raise ValueError('Forløbet skal høre til den valgte aktør.')
    return track_id
