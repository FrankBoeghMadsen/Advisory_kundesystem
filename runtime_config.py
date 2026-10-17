import os
from pathlib import Path


VALID_APP_MODES = {"production", "development", "test"}
PROJECT_DIR = Path(__file__).resolve().parent
APP_MODE = os.environ.get("FRANK_MONITOR_MODE", "").strip().lower()
PRODUCTION_DATA_DIR = Path(
    os.environ.get(
        "FRANK_MONITOR_PRODUCTION_DATA_DIR",
        Path.home() / "FrankAdvisoryMonitorData",
    )
).expanduser().resolve()


def _configured_data_dir():
    configured = os.environ.get("FRANK_MONITOR_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if APP_MODE == "production":
        return PRODUCTION_DATA_DIR
    if APP_MODE == "development":
        return (PROJECT_DIR / ".dev-data").resolve()
    return (PROJECT_DIR / ".unconfigured-data").resolve()


DATA_DIR = _configured_data_dir()


class RuntimeConfigurationError(RuntimeError):
    pass


def validate_data_configuration(
    mode=None,
    data_dir=None,
    production_data_dir=None,
):
    selected_mode = (mode if mode is not None else APP_MODE).strip().lower()
    selected_data_dir = Path(data_dir if data_dir is not None else DATA_DIR).resolve()
    production_dir = Path(
        production_data_dir
        if production_data_dir is not None
        else PRODUCTION_DATA_DIR
    ).resolve()

    if selected_mode not in VALID_APP_MODES:
        raise RuntimeConfigurationError(
            "FRANK_MONITOR_MODE skal sættes eksplicit til production, development eller test."
        )

    if selected_mode == "production":
        if selected_data_dir != production_dir:
            raise RuntimeConfigurationError(
                "Produktionstilstand må kun bruge den fastlagte aktive datamappe."
            )
    elif selected_data_dir == production_dir or production_dir in selected_data_dir.parents:
        raise RuntimeConfigurationError(
            "Udvikling og test må ikke bruge den aktive datamappe eller en undermappe i den."
        )

    return selected_data_dir


def validate_database_write_path(
    path,
    mode=None,
    production_data_dir=None,
):
    selected_mode = (mode if mode is not None else APP_MODE).strip().lower()
    if selected_mode not in VALID_APP_MODES:
        raise RuntimeConfigurationError(
            "Databaseskrivning kræver en eksplicit driftstilstand."
        )
    selected_path = Path(path).resolve()
    production_dir = Path(
        production_data_dir
        if production_data_dir is not None
        else PRODUCTION_DATA_DIR
    ).resolve()
    if selected_mode == "production":
        if production_dir != selected_path.parent and production_dir not in selected_path.parents:
            raise RuntimeConfigurationError(
                "Produktionstilstand må kun skrive i den aktive datamappe."
            )
    elif selected_path == production_dir or production_dir in selected_path.parents:
        raise RuntimeConfigurationError(
            "Udvikling og test må ikke åbne en database i den aktive datamappe til skrivning."
        )
    return selected_path


def mode_label(mode=None):
    selected_mode = (mode if mode is not None else APP_MODE).strip().lower()
    return {
        "production": "DRIFT",
        "development": "UDVIKLING",
        "test": "TEST",
    }.get(selected_mode, "IKKE KONFIGURERET")
