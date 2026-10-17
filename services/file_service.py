from datetime import datetime

from db import UPLOAD_DIR


def save_uploaded_file(company_id, uploaded_file):
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    folder = UPLOAD_DIR / str(company_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return target
