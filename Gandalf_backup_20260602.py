import io
import os
import csv
import time
import shutil
import socket
import subprocess
import tempfile
import msvcrt
import sys
import ctypes
import threading

# Watchdog (Ordnerüberwachung)
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:
    Observer = None
    FileSystemEventHandler = object

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


_STATUS_LINE_GUARD = {'active': False}

# =================================================
# KONFIGURATION
# =================================================

CONFIG = {
    # OrcaScan
    "ORCA_URL": "https://cloud.orcascan.com/sheets/6936ed1cc6cbc485e4c75d28",
    "ORCA_SHEET_TAB_NAME": "Tagesbote",  # EXAKT wie der Tab heißt

    # CDP / Detached Chrome
    "CDP_HOST": "127.0.0.1",
    "CDP_PORT_START": 9222,
    "CDP_PORT_TRIES": 10,
    "CHROME_PROFILE_DIR": Path.cwd() / "PICKUP" / "orca_profile_detached",
    "CHROME_STARTUP_TIMEOUT_SEC": 20,

    # Barcode-Dialog: Dropdown soll auf dieser Option stehen
    "ORCA_BARCODE_MODE_TEXT": "Auto-generate barcodes",

    # CSV Encodings
    "CSV_ENCODINGS": ["utf-8", "utf-8-sig", "latin1", "cp1252"],

    # PICKUP Ordnerstruktur
    "IN_DIR": "IN",
    "OUT_DIR": "OUT",
    "ARCHIVE_DIR": "ARCHIVE",
    "ERROR_DIR": "ERROR",
    "LOG_DIR": "logs",

    # Output-Datei (eine gemergte Datei)
    "MERGED_OUTPUT_FILENAME": "orca_tagesboten.xlsx",

    # BW Filter: Nur Pickup exportieren
    "BW_EXPORT_ONLY_PICKUP": True,
    "BW_PICKUP_VALUE": "pickup",

    # CAF Filter: Nur Pickup exportieren
    "CAF_EXPORT_ONLY_PICKUP": True,
    "CAF_PICKUP_VALUE": "pickup",

    # Ziel-Kiosk Normalisierung (Output)
    "ZIEL_KIOSK_RENAMES": {
        "Cannabis Apotheke Frankfurt": "Kissel",
    },

    "WAWICAN_ABHOLORT_SUBSTRING_MAP": [
        ("ernst-wiss-straße 9, 65933 frankfurt am main", "Ernst"),
        ("madvapes griesheim", "Ernst"),
        ("leipziger straße 20, 60487 frankfurt am main", "Kissel"),
        ("kissel apotheke", "Kissel"),
        ("ostbahnhofstraße 18, 60314 frankfurt am main", "Ost"),
        ("madvapes ostbahnhof", "Ost"),
        ("mörfelder landstr. 225, 60598 frankfurt am main", "Kiosk Mörfelder"),
        ("mörfelder landstr. 245, 60598 frankfurt am main", "Kiosk Mörfelder"),
        ("mörfelders", "Kiosk Mörfelder"),
    ],

    # Datei-Stabilitätscheck
    "FILE_STABLE_SECONDS": 2.0,
    "FILE_STABLE_POLL": 0.4,

    # Welche Extensions wir als Input akzeptieren
    "ALLOWED_SUFFIXES": [".csv", ".xlsx", ".xls"],
    # Optik / Logs
    "VERBOSE": False,                 # True = mehr Detail-Logs
    "USE_ANSI_COLORS": True,          # Farben in Konsole (Windows Terminal/PowerShell meist OK)
    "LOG_DAILY_FILE": True,           # True = ein Log pro Tag
    "CLEANUP_DAYS": 14,               # Logs/Archive/Error älter als X Tage löschen (0 = aus)
    "RUN_SUMMARY_REPORT": False,      # reserviert (aktuell nicht genutzt)
    "BASE_PICKUP_DIR": Path(r"W:\Dokumentenaustausch\Tagesskripte\PICKUP"),

    # Etikettendruck (nach Import)
    "SUMATRA_EXE": str(Path.home() / "AppData" / "Local" / "SumatraPDF" / "SumatraPDF.exe"),
    "LABEL_PRINTER": "ZDesigner Cannabis 28",
    "LABEL_TEMPLATE": "ZDesignerPU",

    # Abholer_DB (OrcaScan REST API)
    "ORCA_API_KEY": "",  # In config_geheim.py setzen
    "ORCA_API_BASE": "https://api.orcascan.com/v1",
    "ABHOLER_DB_SHEET_ID": "68f61e222eeb7a7d51598393",

}


# =================================================
# LOGGING / PAUSE / FILE UTILS
# =================================================


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _today_stamp() -> str:
    return datetime.now().strftime("%Y%m%d")


def _ansi(color: str) -> str:
    if not CONFIG.get("USE_ANSI_COLORS", True):
        return ""
    colors = {
        "reset": "\033[0m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "cyan": "\033[36m",
    }
    return colors.get(color, "")


def _format_line(level: str, msg: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] [{level}] {msg}"


def log_write(log_file: Path, msg: str, level: str = "INFO", *, verbose_only: bool = False) -> None:
    if _STATUS_LINE_GUARD.get('active'):
        try:
            print()
        except Exception:
            pass
        _STATUS_LINE_GUARD['active'] = False

    if verbose_only and not CONFIG.get("VERBOSE", False):
        return

    if CONFIG.get("LOG_DAILY_FILE", True):
        log_file = log_file.parent / f"run__watch__{_today_stamp()}.log"

    line = _format_line(level, msg)

    color = ""
    reset = ""
    if CONFIG.get("USE_ANSI_COLORS", True):
        if level == "OK":
            color, reset = _ansi("green"), _ansi("reset")
        elif level in ("WARN", "WARNING"):
            color, reset = _ansi("yellow"), _ansi("reset")
        elif level in ("ERR", "ERROR"):
            color, reset = _ansi("red"), _ansi("reset")
        else:
            color, reset = "", _ansi("reset")

    print(f"{color}{line}{reset}")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_banner(log_file: Path, title: str) -> None:
    bar = "═" * max(24, len(title) + 6)
    log_write(log_file, bar)
    log_write(log_file, f"  {title}")
    log_write(log_file, bar)


def cleanup_old_files(base_dir: Path, log_file: Path) -> None:
    days = int(CONFIG.get("CLEANUP_DAYS", 0) or 0)
    if days <= 0:
        return
    cutoff = datetime.now() - timedelta(days=days)
    paths = ensure_dirs(base_dir)
    targets = [paths["logs"], paths["archive"], paths["error"]]

    deleted = 0
    for folder in targets:
        try:
            for p in folder.rglob("*"):
                if not p.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime)
                    if mtime < cutoff:
                        p.unlink(missing_ok=True)
                        deleted += 1
                except Exception:
                    pass
        except Exception:
            pass

    if deleted:
        log_write(log_file, f"Cleanup: {deleted} alte Dateien gelöscht (>{days} Tage).", level="OK")


def pause_console(msg: str = "\nDrücke eine Taste, um das Fenster zu schließen...") -> None:
    """
    Robust für Windows: wartet auch dann, wenn stdin nicht verfügbar ist.
    """
    print(msg)
    try:
        input()
        return
    except EOFError:
        pass


def set_console_title(title: str) -> None:
    """
    Setzt den Windows-Konsolen-Titel robust (ohne Spam in stdout).
    """
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(str(title))
    except Exception:
        # Fallback (kann in manchen Umgebungen scheitern, ist aber unkritisch)
        try:
            os.system(f'title {title}')
        except Exception:
            pass

    try:
        msvcrt.getch()
        return
    except Exception:
        while True:
            time.sleep(3600)


def ensure_dirs(base: Path) -> dict[str, Path]:
    pickup = base
    paths = {
        "pickup": pickup,
        "in": pickup / CONFIG["IN_DIR"],
        "out": pickup / CONFIG["OUT_DIR"],
        "archive": pickup / CONFIG["ARCHIVE_DIR"],
        "error": pickup / CONFIG["ERROR_DIR"],
        "logs": pickup / CONFIG["LOG_DIR"],
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def wait_until_file_stable(path: Path, stable_seconds: float, poll: float) -> None:
    last_size = -1
    stable_for = 0.0
    while stable_for < stable_seconds:
        size = path.stat().st_size
        if size == last_size:
            stable_for += poll
        else:
            stable_for = 0.0
            last_size = size
        time.sleep(poll)


def safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        dst = dst_dir / f"{src.stem}__{now_stamp()}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst


def list_queue_files(in_dir: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(in_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in CONFIG["ALLOWED_SUFFIXES"]:
            files.append(p)
    return files


# =================================================
# DATA HELPERS
# =================================================

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.strip('"')
    )
    return df


def build_name(lastname, firstname) -> str:
    ln = str(lastname).strip() if pd.notna(lastname) else ""
    fn = str(firstname).strip() if pd.notna(firstname) else ""
    if ln and fn:
        return f"{ln}, {fn}"
    if ln:
        return ln
    if fn:
        return fn
    return ""


def normalize_ziel_kiosk(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return CONFIG["ZIEL_KIOSK_RENAMES"].get(text, text)


def map_kiosk_wawican(abholort) -> str:
    if pd.isna(abholort):
        return ""
    text = str(abholort).strip()
    lower_text = text.lower()
    for needle, replacement in CONFIG["WAWICAN_ABHOLORT_SUBSTRING_MAP"]:
        if needle in lower_text:
            return replacement
    return text


def map_zahlung_wawican(vor_ort_wert) -> str:
    if pd.isna(vor_ort_wert):
        return ""
    text = str(vor_ort_wert).strip().lower()
    if text == "nein":
        return "Erhalten"
    if text == "ja":
        return "Vor Ort"
    return ""


def parse_mixed_datum(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.astype(str).str.strip(), dayfirst=True, errors="coerce")


# =================================================
# INPUT LOADING
# =================================================

def load_from_xlsx_wawican(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    first_col = raw.iloc[:, 0].dropna().astype(str)

    if len(first_col) < 2:
        raise ValueError("Zu wenig Zeilen in der XLSX (Header + Daten erwartet).")

    header_line = first_col.iloc[0]
    data_lines = first_col.iloc[1:]
    csv_text = header_line + "\n" + "\n".join(data_lines)

    return pd.read_csv(io.StringIO(csv_text), sep=",", engine="python", dtype=str)


def detect_csv_dialect(path: Path, encoding: str) -> tuple[str, str]:
    with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
        sample = f.read(20000)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"
    return delimiter, '"'


def detect_bad_csv_lines(path: Path, encoding: str, delimiter: str, quotechar: str = '"') -> tuple[int, list[int]]:
    bad_lines: list[int] = []
    expected_fields: int | None = None
    with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter, quotechar=quotechar)
        for lineno, row in enumerate(reader, start=1):
            if lineno == 1:
                expected_fields = len(row)
                continue
            if expected_fields is not None and len(row) != expected_fields:
                bad_lines.append(lineno)
    return expected_fields or 0, bad_lines


def load_csv_generic(path: Path, log_file: Path) -> pd.DataFrame:
    last_error = None
    for enc in CONFIG["CSV_ENCODINGS"]:
        try:
            delimiter, quotechar = detect_csv_dialect(path, encoding=enc)
            log_write(log_file, f"[CSV] Datei={path.name} | Encoding={enc} | Delimiter='{delimiter}'")

            try:
                df = pd.read_csv(
                    path,
                    sep=delimiter,
                    engine="python",
                    encoding=enc,
                    quotechar=quotechar,
                    dtype=str,
                )
                log_write(log_file, f"[CSV] OK | Zeilen={len(df)} | Spalten={len(df.columns)}")
                return df
            except Exception as e:
                last_error = e

            expected_fields, bad_lines = detect_bad_csv_lines(path, encoding=enc, delimiter=delimiter, quotechar=quotechar)
            df = pd.read_csv(
                path,
                sep=delimiter,
                engine="python",
                encoding=enc,
                quotechar=quotechar,
                dtype=str,
                on_bad_lines="skip",
            )

            skipped = len(bad_lines)
            log_write(
                log_file,
                f"[CSV] OK (bad lines skipped) | Zeilen={len(df)} | Spalten={len(df.columns)} | Übersprungen={skipped} | Expected={expected_fields}"
            )
            return df

        except Exception as e:
            last_error = e

    raise RuntimeError(f"CSV konnte nicht eingelesen werden. Letzter Fehler: {last_error}")


def load_any_input(path: Path, log_file: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        return load_from_xlsx_wawican(path)
    if suffix == ".csv":
        return load_csv_generic(path, log_file)
    raise ValueError(f"Nicht unterstützter Dateityp: {suffix}")


# =================================================
# STRUCTURE DETECTION + BUILD
# =================================================

def is_bw_structure(df: pd.DataFrame) -> bool:
    cols = set(df.columns)
    required = {
        "OrderNumber", "DateOfOrder", "Shipping_FirstName", "Shipping_LastName",
        "Pharmacy", "Total", "DeliveryOption", "PaymentStatus", "Status"
    }
    return required.issubset(cols)


def is_caf_structure(df: pd.DataFrame) -> bool:
    cols = set(df.columns)
    required = {"Best.-Nr.", "Datum", "Name", "Bestellwert", "Lieferung", "Zahlung", "Status"}
    return required.issubset(cols)


ORCA_COLS = [
    "Paket-Barcode", "Datum", "Name", "Ziel-Kiosk", "Status",
    "Bestellwert", "Versicher.", "Lieferung", "Zahlung",
]


def build_orca_from_bw(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "OrderNumber", "DateOfOrder", "Shipping_FirstName", "Shipping_LastName",
        "Pharmacy", "Status", "Total", "DeliveryOption", "PaymentStatus"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[BW] Fehlende Spalten: {missing}")

    if CONFIG["BW_EXPORT_ONLY_PICKUP"]:
        pickup_value = str(CONFIG["BW_PICKUP_VALUE"]).strip().lower()
        mask = df["DeliveryOption"].astype(str).str.strip().str.lower() == pickup_value
        df = df[mask].copy()

    sort_series = pd.to_datetime(df["DateOfOrder"].astype(str).str.strip(), format="%d.%m.%Y", errors="coerce")
    df = df.assign(_sort_date=sort_series).sort_values("_sort_date", ascending=True).drop(columns="_sort_date")

    out = pd.DataFrame()
    out["Paket-Barcode"] = df["OrderNumber"]
    out["Datum"] = df["DateOfOrder"]
    out["Name"] = [build_name(ln, fn) for ln, fn in zip(df["Shipping_LastName"], df["Shipping_FirstName"])]
    out["Ziel-Kiosk"] = df["Pharmacy"].apply(normalize_ziel_kiosk)
    out["Status"] = df["Status"]
    out["Bestellwert"] = df["Total"]
    out["Versicher."] = ""
    out["Lieferung"] = df["DeliveryOption"]
    out["Zahlung"] = df["PaymentStatus"]
    return out[ORCA_COLS]


def build_orca_from_caf(df: pd.DataFrame) -> pd.DataFrame:
    required = ["Best.-Nr.", "Datum", "Name", "Bestellwert", "Lieferung", "Zahlung", "Status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[CAF] Fehlende Spalten: {missing}")
    # Spalte heißt je nach CAF-Version "Versicherung" (neu) oder "Versicher." (alt)
    if "Versicherung" in df.columns:
        versicher_col = "Versicherung"
    elif "Versicher." in df.columns:
        versicher_col = "Versicher."
    else:
        raise ValueError("[CAF] Fehlende Spalte: Versicherung oder Versicher.")

    # Zeilen herausfiltern, wo die Bestellnummer eine URL ist (Metadaten-Zeilen im CAF-Export)
    df = df[~df["Best.-Nr."].astype(str).str.strip().str.startswith("http")].copy()

    if CONFIG["CAF_EXPORT_ONLY_PICKUP"]:
        # Akzeptiert altes Format ("pickup") und neues Format ("Abholung"), Groß-/Kleinschreibung egal
        lieferung_lower = df["Lieferung"].astype(str).str.strip().str.lower()
        mask = lieferung_lower.isin({"pickup", "abholung"})
        df = df[mask].copy()

    # Datum: altes Format "dd.mm.yyyy HH:MM" oder neues Format "dd.mm.yy HH:MM" (zweistelliges Jahr)
    datum_str = df["Datum"].astype(str).str.strip()
    sort_series = pd.to_datetime(datum_str, format="%d.%m.%y %H:%M", errors="coerce")
    sort_series = sort_series.fillna(pd.to_datetime(datum_str, format="%d.%m.%Y %H:%M", errors="coerce"))
    df = df.assign(_sort_date=sort_series).sort_values("_sort_date", ascending=True).drop(columns="_sort_date")

    # Neues CAF-Format: Name-Spalte enthält "Vorname Nachname, Stadt" -> Lieferung-Name nur den Namen
    name_col = "Lieferung-Name" if "Lieferung-Name" in df.columns else "Name"

    out = pd.DataFrame()
    out["Paket-Barcode"] = df["Best.-Nr."]
    out["Datum"] = df["Datum"]
    out["Name"] = df[name_col]
    out["Ziel-Kiosk"] = ""
    out["Status"] = df["Status"]
    out["Bestellwert"] = df["Bestellwert"]
    out["Versicher."] = df[versicher_col]
    out["Lieferung"] = df["Lieferung"]
    out["Zahlung"] = df["Zahlung"]
    return out[ORCA_COLS]


def build_orca_from_wawican(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "Id", "Reservierungsdatum", "Vorname", "Nachname", "Abholort", "Status",
        "Rechnungsbetrag", "Versichertenstatus", "Lieferart", "vor Ort Zahlung"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[WAWICAN] Fehlende Spalten: {missing}")

    # Zeilen herausfiltern, wo die Id eine URL ist (Metadaten-/Link-Zeilen im WAWICAN-Export)
    # Zusätzlich: Zeilen ohne Nachname oder ohne Datum rausfiltern (weitere Schutzebene)
    id_is_url   = df["Id"].astype(str).str.strip().str.startswith("http")
    name_empty  = df["Nachname"].astype(str).str.strip().isin(["", "nan", "NaN"])
    datum_empty = df["Reservierungsdatum"].astype(str).str.strip().isin(["", "nan", "NaN"])
    df = df[~(id_is_url | name_empty | datum_empty)].copy()

    mask = df["Lieferart"].astype(str).str.strip().str.lower() == "abholer"
    df = df[mask].copy()

    sort_series = pd.to_datetime(df["Reservierungsdatum"].astype(str).str.strip(), format="%d.%m.%Y", errors="coerce")
    df = df.assign(_sort_date=sort_series).sort_values("_sort_date", ascending=True).drop(columns="_sort_date")

    out = pd.DataFrame()
    out["Paket-Barcode"] = df["Id"]
    out["Datum"] = df["Reservierungsdatum"]
    out["Name"] = [build_name(ln, fn) for ln, fn in zip(df["Nachname"], df["Vorname"])]
    out["Ziel-Kiosk"] = df["Abholort"].apply(map_kiosk_wawican).apply(normalize_ziel_kiosk)
    out["Status"] = df["Status"]
    out["Bestellwert"] = df["Rechnungsbetrag"]
    out["Versicher."] = df["Versichertenstatus"]
    out["Lieferung"] = df["Lieferart"]
    out["Zahlung"] = df["vor Ort Zahlung"].apply(map_zahlung_wawican)
    return out[ORCA_COLS]


def detect_and_build_orca(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    if is_bw_structure(df):
        return "BW", build_orca_from_bw(df)
    if is_caf_structure(df):
        return "CAF", build_orca_from_caf(df)
    return "WAWICAN", build_orca_from_wawican(df)


# =================================================
# ABHOLER_DB: PAKETE PER REST API ANLEGEN
# =================================================

def post_to_abholer_db(orca_df: pd.DataFrame, log_file: Path) -> int:
    """Legt alle Zeilen aus orca_df als neue Pakete in der Abholer_DB an."""
    import json
    import urllib.request
    import urllib.error

    sheet_id = CONFIG["ABHOLER_DB_SHEET_ID"]
    api_key = CONFIG["ORCA_API_KEY"]
    url = f"{CONFIG['ORCA_API_BASE']}/sheets/{sheet_id}/rows"
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today_iso = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")

    log_write(log_file, f"[ABHOLER_DB] Lege {len(orca_df)} Pakete in Abholer_DB an...")

    created = 0
    failed = 0
    for _, row in orca_df.iterrows():
        barcode = str(row.get("Paket-Barcode", "")).strip()
        name = str(row.get("Name", "")).strip()
        kiosk = str(row.get("Ziel-Kiosk", "")).strip()
        zahlung = str(row.get("Zahlung", "")).strip()
        bestellwert = str(row.get("Bestellwert", "")).strip()
        if not barcode:
            continue

        payload_dict = {
            "barcode": barcode,
            "receipiantName": name,
            "location": "Nicht verpackt",
            "zahlung": zahlung,
            "date": today_iso,
            "verpacktu005fat": now_iso,
        }
        if kiosk:
            payload_dict["zielu002dkiosk"] = kiosk
        if bestellwert:
            payload_dict["bestellwert"] = bestellwert

        try:
            payload = json.dumps(payload_dict).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            created += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            log_write(log_file, f"[ABHOLER_DB] HTTP {e.code} für {barcode}: {body}", level="WARN")
            failed += 1
        except Exception as e:
            log_write(log_file, f"[ABHOLER_DB] Fehler für {barcode}: {e}", level="WARN")
            failed += 1

    level = "OK" if failed == 0 else "WARN"
    log_write(log_file, f"[ABHOLER_DB] Angelegt: {created} | Fehler: {failed}", level=level)
    return created


# =================================================
# STEP 1: QUEUE -> MERGED ORCA FILE
# =================================================

def process_pickup_queue_merge(base_dir: Path, log_file: Path) -> tuple[Path | None, int, int, int]:
    paths = ensure_dirs(base_dir)
    queue = list_queue_files(paths["in"])

    if not queue:
        log_write(log_file, "Keine Dateien in PICKUP\\IN gefunden.")
        return None, 0, 0, 0, None

    all_parts: list[pd.DataFrame] = []
    processed = 0
    failed = 0

    for file_path in queue:
        log_write(log_file, f"---\nQueue: {file_path.name}")
        try:
            wait_until_file_stable(file_path, CONFIG["FILE_STABLE_SECONDS"], CONFIG["FILE_STABLE_POLL"])
            df = load_any_input(file_path, log_file)
            df = clean_columns(df)

            source, orca_df = detect_and_build_orca(df)
            log_write(log_file, f"Erkannt: {source} | ORCA-Zeilen: {len(orca_df)}")

            if len(orca_df) > 0:
                all_parts.append(orca_df)

            archived_to = safe_move(file_path, paths["archive"])
            log_write(log_file, f"Archiviert: {archived_to.name}")
            processed += 1

        except Exception as e:
            failed += 1
            log_write(log_file, f"FEHLER: {e}")
            try:
                errored_to = safe_move(file_path, paths["error"])
                log_write(log_file, f"Nach ERROR verschoben: {errored_to.name}")
            except Exception as me:
                log_write(log_file, f"Konnte ERROR-Verschiebung nicht ausführen: {me}")

    log_write(log_file, f"Queue fertig. Processed={processed} | Failed={failed}")

    if not all_parts:
        log_write(log_file, "Keine ORCA-Daten zum Export (alle leer oder fehlgeschlagen).")
        return None, processed, failed, 0, None

    merged = pd.concat(all_parts, ignore_index=True)
    merged = (
        merged.assign(_sort_date=parse_mixed_datum(merged["Datum"]))
        .sort_values("_sort_date", ascending=True)
        .drop(columns="_sort_date")
    )

    out_path = paths["out"] / CONFIG["MERGED_OUTPUT_FILENAME"]
    merged.to_excel(out_path, index=False)
    log_write(log_file, f"MERGE EXPORT OK: {out_path} | Gesamtzeilen={len(merged)}")
    return out_path, processed, failed, len(merged), merged


# =================================================
# CDP / DETACHED CHROME
# =================================================

def _is_port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _find_chrome_exe() -> Path:
    local = Path.home() / "AppData" / "Local"
    program_files = Path("C:/Program Files")
    program_files_x86 = Path("C:/Program Files (x86)")

    candidates = [
        program_files / "Google/Chrome/Application/chrome.exe",
        program_files_x86 / "Google/Chrome/Application/chrome.exe",
        local / "Google/Chrome/Application/chrome.exe",
    ]

    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError("Chrome nicht gefunden. Bitte Chrome installieren oder Pfad anpassen.")


def _start_detached_chrome(host: str, port: int, profile_dir: Path, log_file: Path) -> None:
    exe = _find_chrome_exe()
    profile_dir.mkdir(parents=True, exist_ok=True)

    args = [
        str(exe),
        f"--remote-debugging-port={port}",
        f"--remote-debugging-address={host}",
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--start-maximized",
        "about:blank",
    ]

    creationflags = 0
    creationflags |= subprocess.DETACHED_PROCESS
    creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP

    log_write(log_file, f"Starte detached Chrome: Port={port} | Profil={profile_dir}")
    subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
        shell=False,
    )


def ensure_cdp_browser_ready(log_file: Path) -> tuple[str, int]:
    host = CONFIG["CDP_HOST"]

    # existiert schon?
    for i in range(CONFIG["CDP_PORT_TRIES"]):
        port = CONFIG["CDP_PORT_START"] + i
        if _is_port_open(host, port):
            log_write(log_file, f"CDP bereits verfügbar auf {host}:{port}")
            return host, port

    # sonst starten
    for i in range(CONFIG["CDP_PORT_TRIES"]):
        port = CONFIG["CDP_PORT_START"] + i
        if _is_port_open(host, port):
            continue

        _start_detached_chrome(host, port, CONFIG["CHROME_PROFILE_DIR"], log_file)

        t0 = time.time()
        while time.time() - t0 < CONFIG["CHROME_STARTUP_TIMEOUT_SEC"]:
            if _is_port_open(host, port):
                log_write(log_file, f"CDP bereit auf {host}:{port}")
                return host, port
            time.sleep(0.25)

        log_write(log_file, f"WARNUNG: Port {port} wurde nicht rechtzeitig bereit. Nächster Versuch...")

    raise RuntimeError("Konnte keinen CDP-Browser starten/finden.")


# =================================================
# ORCA UI AUTOMATION (CDP)
# =================================================

def click_if_exists(locator, timeout_ms: int = 1500) -> bool:
    try:
        locator.first.wait_for(state="visible", timeout=timeout_ms)
        locator.first.click()
        return True
    except Exception:
        return False


def goto_sheet_tab_if_needed(page, log_file: Path) -> None:
    name = CONFIG["ORCA_SHEET_TAB_NAME"]
    if click_if_exists(page.get_by_role("tab", name=name), timeout_ms=1500):
        log_write(log_file, f"Tab gewechselt: {name} (role=tab)")
        return
    if click_if_exists(page.get_by_text(name, exact=True), timeout_ms=1500):
        log_write(log_file, f"Tab gewechselt: {name} (Text)")
        return
    log_write(log_file, f"Tab '{name}' nicht explizit klickbar gefunden (evtl. schon aktiv).")


# =================================================
# ORCA PURE-DIALOG HELPERS (NEU)
# =================================================

def wait_pure_dialog(page, title_contains: str, log_file: Path, timeout_ms: int = 20000):
    dlg = page.locator("pure-dialog:visible").filter(has=page.get_by_text(title_contains, exact=False)).first
    log_write(log_file, f"Warte auf Dialog: '{title_contains}' ...")
    dlg.wait_for(state="visible", timeout=timeout_ms)
    return dlg


def pure_dialog_click_value(page, title_contains: str, button_value: str, log_file: Path, timeout_ms: int = 20000):
    dlg = wait_pure_dialog(page, title_contains=title_contains, log_file=log_file, timeout_ms=timeout_ms)
    btn = dlg.locator(f'input[type="button"][value="{button_value}"]:visible:visible').first
    log_write(log_file, f"Klicke im Dialog '{title_contains}': value='{button_value}' ...")
    btn.wait_for(state="visible", timeout=timeout_ms)
    btn.click()
    page.wait_for_timeout(400)


def ensure_dialog_dropdown_text(page, dlg, desired_text: str, log_file: Path, timeout_ms: int = 10000):
    if dlg.get_by_text(desired_text, exact=False).count() > 0:
        log_write(log_file, f"Dropdown steht bereits auf: {desired_text}")
        return

    log_write(log_file, f"Setze Dropdown auf: {desired_text} ...")

    trigger_candidates = [
        dlg.locator('[role="combobox"]'),
        dlg.locator("pure-select"),
        dlg.locator(".pure-select"),
        dlg.locator("pure-dropdown"),
        dlg.locator(".pure-dropdown"),
        dlg.locator("input[readonly]"),
    ]

    opened = False
    for tr in trigger_candidates:
        try:
            if tr.count() > 0 and tr.first.is_visible():
                tr.first.click()
                opened = True
                break
        except Exception:
            pass

    if not opened:
        try:
            arrow = dlg.locator("svg, i").first
            if arrow.is_visible():
                arrow.click()
                opened = True
        except Exception:
            pass

    if opened:
        opt = page.get_by_text(desired_text, exact=False).first
        opt.wait_for(state="visible", timeout=timeout_ms)
        opt.click()
        page.wait_for_timeout(300)

        if dlg.get_by_text(desired_text, exact=False).count() > 0:
            log_write(log_file, f"Dropdown gesetzt auf: {desired_text}")
        else:
            log_write(log_file, f"WARNUNG: Dropdown-Text '{desired_text}' nach Auswahl nicht sichtbar.")
    else:
        log_write(log_file, "WARNUNG: Dropdown konnte nicht geöffnet werden (best effort).")


def pure_dialog_set_dropdown_and_click(
    page,
    title_contains: str,
    dropdown_text: str,
    button_value: str,
    log_file: Path,
    timeout_ms: int = 20000
):
    dlg = wait_pure_dialog(page, title_contains=title_contains, log_file=log_file, timeout_ms=timeout_ms)
    ensure_dialog_dropdown_text(page, dlg, desired_text=dropdown_text, log_file=log_file, timeout_ms=min(10000, timeout_ms))
    btn = dlg.locator(f'input[type="button"][value="{button_value}"]:visible:visible').first
    log_write(log_file, f"Klicke im Dialog '{title_contains}': value='{button_value}' ...")
    btn.wait_for(state="visible", timeout=timeout_ms)
    btn.click()
    page.wait_for_timeout(400)


def upload_merged_file_via_cdp(merged_xlsx: Path, log_file: Path) -> None:
    if not merged_xlsx.exists():
        raise FileNotFoundError(f"Upload-Datei fehlt: {merged_xlsx}")

    host, port = ensure_cdp_browser_ready(log_file)
    endpoint = f"http://{host}:{port}"
    log_write(log_file, f"Verbinde per CDP: {endpoint}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(endpoint)

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        log_write(log_file, f"Öffne Orca: {CONFIG['ORCA_URL']}")
        page.goto(CONFIG["ORCA_URL"], wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        goto_sheet_tab_if_needed(page, log_file)

        toolbar_import = page.get_by_role("button", name="Importieren")

        try:
            toolbar_import.wait_for(state="visible", timeout=6000)
        except PlaywrightTimeoutError:
            log_write(log_file, "Button 'Importieren' nicht sichtbar -> vermutlich nicht eingeloggt.")
            log_write(log_file, "Bitte im geöffneten Chrome einloggen. Ich warte...")
            toolbar_import.wait_for(state="visible", timeout=10 * 60 * 1000)
            log_write(log_file, "Login erkannt. Weiter...")

        goto_sheet_tab_if_needed(page, log_file)

        # Zeilenzahl vor Import merken
        rows_before = get_orca_row_count(page)
        log_write(log_file, f"Zeilen vor Import: {rows_before}")

        log_write(log_file, "Klicke Toolbar 'Importieren' ...")
        toolbar_import.click()
        page.wait_for_timeout(1200)

        file_input = page.locator("input[type='file']")
        file_input.first.wait_for(state="attached", timeout=15000)

        merged_abs = merged_xlsx.resolve()
        log_write(log_file, f"Setze Datei via input[type=file]: {merged_abs.name}")
        file_input.first.set_input_files(str(merged_abs))

        # Schritt 1: Dialog "Tabelle importieren" -> Importieren
        pure_dialog_click_value(
            page=page,
            title_contains="Tabelle importieren",
            button_value="Importieren",
            log_file=log_file,
            timeout_ms=20000
        )

        # Schritt 2: Dialog "Importieren" (Barcode) -> Dropdown sicherstellen -> Importieren
        pure_dialog_set_dropdown_and_click(
            page=page,
            title_contains="Importieren",
            dropdown_text=CONFIG["ORCA_BARCODE_MODE_TEXT"],  # "Auto-generate barcodes"
            button_value="Importieren",
            log_file=log_file,
            timeout_ms=20000
        )

        # Schritt 3: Dialog "Import erfolgreich" -> Ok
        pure_dialog_click_value(
            page=page,
            title_contains="Import erfolgreich",
            button_value="Ok",
            log_file=log_file,
            timeout_ms=30000
        )

        # Zeilenzahl nach Import messen
        page.wait_for_timeout(1000)  # kurz warten bis Statusbar aktualisiert
        rows_after = get_orca_row_count(page)
        log_write(log_file, f"Zeilen nach Import: {rows_after} (+{rows_after - rows_before} neu)")

        log_write(log_file, "Import abgeschlossen.")

        # Etiketten drucken (nur neue Zeilen)
        print_labels(page, log_file, rows_before=rows_before, rows_after=rows_after)

        log_write(log_file, "Chrome/Orca bleibt offen (detached).")
        # Wichtig: kein browser.close()



# =================================================
# LABEL DRUCK (NACH IMPORT)
# =================================================

def get_orca_row_count(page) -> int:
    """Liest die aktuelle Zeilenzahl aus dem OrcaScan Statusbar."""
    try:
        val = page.locator("#statusbarSheetRows").get_attribute("data-value", timeout=3000)
        if val and str(val).strip().isdigit():
            return int(val)
    except Exception:
        pass
    try:
        val = page.locator("[id^='pure-grid-container']").get_attribute("data-count", timeout=2000)
        if val and str(val).strip().isdigit():
            return int(val)
    except Exception:
        pass
    return 0


def _grid_scroll_to_index(page, i: int) -> None:
    """
    Scrollt das virtuelle Grid so, dass die Zeile mit data-index i gerendert wird.
    Sucht den scrollbaren Container selbst (egal wie er heißt) und springt anhand
    der gemessenen Zeilenhöhe an die passende Position.
    """
    page.evaluate(
        """(i) => {
            const rows = Array.from(document.querySelectorAll('tr[data-index]'));
            if (!rows.length) return;
            let scroller = null, el = rows[0];
            while (el) {
                const s = getComputedStyle(el);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) { scroller = el; break; }
                el = el.parentElement;
            }
            if (!scroller) return;
            const rh = rows[0].getBoundingClientRect().height || 30;
            scroller.scrollTop = Math.max(0, i * rh - scroller.clientHeight / 2);
        }""",
        i,
    )


def _label_select_new_rows(page, log_file: Path, rows_before: int, rows_after: int) -> int:
    """
    Wählt NUR die neu importierten Zeilen aus (über data-index).
    Scrollt das virtuelle Grid gezielt zu jeder Zeile, damit sie gerendert wird.
    Gibt die Anzahl markierter Zeilen zurück.
    KEIN 'alle auswählen'-Fallback: Bei Misserfolg wird 0 zurückgegeben –
    der Aufrufer überspringt dann den Druck (lieber nichts drucken als alles).
    """
    n_new = rows_after - rows_before
    if n_new <= 0:
        log_write(log_file, "  WARNUNG: Keine neuen Zeilen erkannt – Druck wird übersprungen.", level="WARN")
        return 0

    log_write(log_file, f"  Wähle Zeilen {rows_before + 1}–{rows_after} ({n_new} neue Zeilen)...")

    selected = 0
    try:
        # Zuerst ans Tabellenende scrollen, damit die neuen Zeilen unten gerendert werden
        _grid_scroll_to_index(page, rows_after)
        page.wait_for_timeout(400)

        for i in range(rows_before, rows_after):
            th = page.locator(f'tr[data-index="{i}"] th[data-row-header="true"]')
            # Falls die Zeile (noch) nicht gerendert ist: gezielt hinscrollen und erneut versuchen
            if th.count() == 0:
                _grid_scroll_to_index(page, i)
                page.wait_for_timeout(250)
                th = page.locator(f'tr[data-index="{i}"] th[data-row-header="true"]')
            if th.count() == 0:
                log_write(log_file, f"  WARNUNG: tr[data-index='{i}'] nicht gefunden (auch nach Scroll).", level="WARN")
                continue
            # Sicher ins Sichtfeld bringen und Locator neu holen (Grid rendert beim Scrollen neu)
            th.scroll_into_view_if_needed(timeout=3000)
            page.wait_for_timeout(150)
            th = page.locator(f'tr[data-index="{i}"] th[data-row-header="true"]')
            # Erste Zeile: normaler Klick (startet Auswahl); weitere: Ctrl+Klick (ergänzt)
            if selected == 0:
                th.click(position={"x": 5, "y": 5})
            else:
                th.click(position={"x": 5, "y": 5}, modifiers=["Control"])
            selected += 1
            page.wait_for_timeout(120)

        page.wait_for_timeout(300)
        log_write(log_file, f"  {selected} von {n_new} Zeilen ausgewählt.")

    except Exception as e:
        log_write(log_file, f"  WARNUNG: Zeilenauswahl fehlgeschlagen ({e}).", level="WARN")

    return selected


def _label_select_all_rows(page, log_file: Path) -> None:
    """Klickt die 'Alle auswählen' Checkbox im Tabellen-Header (Fallback)."""
    log_write(log_file, "Etiketten: Wähle alle Zeilen aus (Fallback)...")
    candidates = [
        page.locator("th input[type='checkbox']").first,
        page.locator("thead input[type='checkbox']").first,
        page.locator(".pure-grid-row-header input[type='checkbox']").first,
    ]
    for c in candidates:
        try:
            if c.count() > 0 and c.is_visible(timeout=1000):
                c.click()
                page.wait_for_timeout(800)
                log_write(log_file, "  Alle Zeilen ausgewählt.")
                return
        except Exception:
            continue
    log_write(log_file, "  WARNUNG: Alle-Auswählen Checkbox nicht gefunden.", level="WARN")


def _label_open_dialog(page, log_file: Path) -> None:
    """Öffnet das Etiketten-Seitenpanel und den 'Etiketten drucken' Dialog."""
    log_write(log_file, "Etiketten: Öffne Etiketten-Panel...")
    # Panel nur öffnen wenn es noch nicht sichtbar ist (Toggle würde es sonst schließen)
    panel_body = page.locator(".barcode-preview-body")
    if not panel_body.is_visible():
        toggle = page.locator("#barcodePreviewOpen")
        try:
            toggle.click(force=True)
        except Exception:
            page.evaluate(
                "document.querySelector('#barcodePreviewOpen')"
                " && document.querySelector('#barcodePreviewOpen').click()"
            )
    panel_body.wait_for(state="visible", timeout=8000)
    log_write(log_file, "  Panel offen. Klicke 'Drucken'...")
    print_btn = page.locator("#barcodePreviewForm input[value='Drucken']")
    print_btn.wait_for(state="visible", timeout=5000)
    # JS-Click umgeht Viewport-Einschränkungen
    page.evaluate("document.querySelector('#barcodePreviewForm input[value=\"Drucken\"]').click()")
    page.locator("div.pure-dialog-title").wait_for(state="visible", timeout=8000)
    log_write(log_file, "  Dialog 'Etiketten drucken' geöffnet.")


def _label_select_type(page, log_file: Path, label_name: str = "ZDesignerPU") -> None:
    """Wählt den Etikettentyp im Dialog."""
    log_write(log_file, f"Etiketten: Wähle Typ '{label_name}'...")
    try:
        dialog = page.locator("#editDialog")
        option = dialog.get_by_text(label_name, exact=False).first
        option.wait_for(state="visible", timeout=8000)
        option.click()
        log_write(log_file, f"  Typ '{label_name}' ausgewählt.")
    except Exception as e:
        log_write(log_file, f"  WARNUNG: Typ '{label_name}' nicht gefunden: {e}", level="WARN")


def _label_download(page, log_file: Path) -> bytes:
    """Klickt 'Herunterladen' im Dialog und gibt die PDF-Bytes zurück."""
    log_write(log_file, "Etiketten: Starte PDF-Download...")
    btn = page.locator("#editDialog").get_by_role("button", name="Herunterladen")
    btn.wait_for(state="visible", timeout=5000)
    with page.expect_download(timeout=30000) as dl_info:
        btn.click()
    download = dl_info.value
    log_write(log_file, f"  PDF heruntergeladen: {download.suggested_filename}")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    download.save_as(str(tmp_path))
    pdf_bytes = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    log_write(log_file, f"  PDF-Größe: {len(pdf_bytes)} Bytes")
    return pdf_bytes


def _label_print_sumatra(pdf_bytes: bytes, log_file: Path) -> None:
    """Druckt PDF via SumatraPDF lautlos an den konfigurierten Etikettendrucker."""
    sumatra = str(CONFIG.get("SUMATRA_EXE", ""))
    printer = str(CONFIG.get("LABEL_PRINTER", ""))
    if not sumatra or not Path(sumatra).exists():
        log_write(log_file, f"  WARNUNG: SumatraPDF nicht gefunden ({sumatra}). Druck übersprungen.", level="WARN")
        return
    if not printer:
        log_write(log_file, "  WARNUNG: LABEL_PRINTER nicht konfiguriert. Druck übersprungen.", level="WARN")
        return
    log_write(log_file, f"Etiketten: Drucke via SumatraPDF -> {printer}...")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [sumatra, "-print-to", printer, "-print-settings", "fit,landscape", "-exit-when-done", str(tmp_path)],
            timeout=60,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log_write(log_file, "  Druckauftrag gesendet.", level="OK")
        else:
            log_write(log_file, f"  WARNUNG: SumatraPDF Exit-Code {result.returncode}", level="WARN")
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


def print_labels(page, log_file: Path, rows_before: int = 0, rows_after: int = 0) -> None:
    """
    Druckt nach dem Import die neu importierten Etiketten:
    Neue Zeilen auswählen → Panel öffnen → Dialog → Template wählen → PDF laden → Drucken.
    rows_before / rows_after: Zeilenzahl vor/nach Import für gezielte Auswahl.
    Wird übersprungen wenn SUMATRA_EXE oder LABEL_PRINTER nicht konfiguriert sind.
    """
    sumatra = str(CONFIG.get("SUMATRA_EXE", ""))
    printer = str(CONFIG.get("LABEL_PRINTER", ""))
    if not sumatra or not printer:
        log_write(log_file, "Etikettendruck deaktiviert (SUMATRA_EXE oder LABEL_PRINTER fehlt in CONFIG).")
        return
    try:
        selected = _label_select_new_rows(page, log_file, rows_before=rows_before, rows_after=rows_after)
        if selected <= 0:
            log_write(log_file, "Etikettendruck ÜBERSPRUNGEN: keine Zeilen markiert – es wird NICHTS gedruckt.", level="WARN")
            return
        _label_open_dialog(page, log_file)
        pdf_bytes = _label_download(page, log_file)
        _label_print_sumatra(pdf_bytes, log_file)
        log_write(log_file, "Etikettendruck abgeschlossen.", level="OK")
    except Exception as e:
        log_write(log_file, f"FEHLER beim Etikettendruck: {e}", level="ERR")


# =================================================
# WATCHDOG: PICKUP\\IN ÜBERWACHEN + DEBOUNCE
# =================================================

def _is_relevant_queue_file(path: Path) -> bool:
    """
    Filtert nur echte Input-Dateien.
    - Endungen: CONFIG["ALLOWED_SUFFIXES"]
    - ignoriert temporäre Office-Dateien (~$...)
    """
    try:
        if not path:
            return False
        if path.name.startswith("~$"):
            return False
        if path.suffix.lower() not in CONFIG["ALLOWED_SUFFIXES"]:
            return False
        return True
    except Exception:
        return False


class PickupInHandler(FileSystemEventHandler):
    """
    Watchdog-Handler: sammelt Events und triggert nach Debounce ein Processing.
    """
    def __init__(self, in_dir: Path, on_trigger, log_file: Path, debounce_sec: float = 4.0):
        super().__init__()
        self.in_dir = in_dir
        self.on_trigger = on_trigger
        self.log_file = log_file
        self.debounce_sec = debounce_sec

        self._timer = None
        self._lock = threading.Lock()

    def _schedule(self):
        with self._lock:
            if self._timer is not None:
                try:
                    self._timer.cancel()
                except Exception:
                    pass
            self._timer = threading.Timer(self.debounce_sec, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self):
        try:
            self.on_trigger()
        except Exception as e:
            log_write(self.log_file, f"[WATCHDOG] Trigger-Fehler: {e}")

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if _is_relevant_queue_file(p):
            log_write(self.log_file, f"[WATCHDOG] created: {p.name}")
            self._schedule()

    def on_modified(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if _is_relevant_queue_file(p):
            self._schedule()

    def on_moved(self, event):
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", "") or event.src_path
        p = Path(dest)
        if _is_relevant_queue_file(p):
            log_write(self.log_file, f"[WATCHDOG] moved: {p.name}")
            self._schedule()


# =================================================
# MAIN
# =================================================

def main():
    base_dir = CONFIG["BASE_PICKUP_DIR"]
    if not base_dir.exists():
        print(f"FEHLER: BASE_PICKUP_DIR nicht erreichbar: {base_dir}")
        pause_console("\nPfad nicht erreichbar. Drücke eine Taste zum Schließen...")
        return
    paths = ensure_dirs(base_dir)
    log_file = paths["logs"] / f"run__watch__{now_stamp()}.log"

    log_banner(log_file, "Gandalf Watcher gestartet")
    log_write(log_file, f"BaseDir={base_dir}")
    log_write(log_file, f"Überwache: {paths['in']}")

    cleanup_old_files(base_dir, log_file)

    if Observer is None:
        log_write(log_file, "FEHLER: watchdog ist nicht installiert.")
        log_write(log_file, "Bitte ausführen: pip install watchdog")
        pause_console("\nWatchdog fehlt. Drücke eine Taste zum Schließen...")
        return

    run_lock = threading.Lock()
    state = {"running": False, "pending": False}
    start_ts = datetime.now()
    counters = {
        "runs": 0,
        "processed_files": 0,
        "failed_files": 0,
        "last_run_ts": "-",
        "last_run_rows": 0,
    }

    def run_pipeline():
        """
        Führt genau einen kompletten Run aus (merge + upload).
        Wenn währenddessen neue Dateien kommen, wird danach automatisch ein weiterer Run gestartet.
        """
        with run_lock:
            if state["running"]:
                state["pending"] = True
                log_write(log_file, "[WATCHDOG] Run läuft bereits -> pending=True")
                return
            state["running"] = True

        try:
            log_write(log_file, "[WATCHDOG] Starte Run ...")
            merged_file, processed, failed, total_rows, merged_df = process_pickup_queue_merge(base_dir, log_file)
            if merged_file is None:
                counters["runs"] += 1
                counters["processed_files"] += processed
                counters["failed_files"] += failed
                counters["last_run_rows"] = total_rows
                counters["last_run_ts"] = datetime.now().strftime("%H:%M:%S")
                log_write(log_file, "[WATCHDOG] Keine Export-Datei erstellt (IN leer oder alles gefiltert).", level="WARN")
            else:
                upload_merged_file_via_cdp(merged_file, log_file)
                try:
                    post_to_abholer_db(merged_df, log_file)
                except Exception as e:
                    log_write(log_file, f"[ABHOLER_DB] Fehler beim Anlegen: {e}", level="ERR")
                counters["runs"] += 1
                counters["processed_files"] += processed
                counters["failed_files"] += failed
                counters["last_run_rows"] = total_rows
                counters["last_run_ts"] = datetime.now().strftime("%H:%M:%S")
                log_write(log_file, f"[WATCHDOG] Run fertig. Dateien: {processed} ok, {failed} fail | Zeilen: {total_rows}", level="OK")
        except Exception as e:
            log_write(log_file, f"[WATCHDOG] Run-Fehler: {e}")
        finally:
            with run_lock:
                state["running"] = False
                pending = state["pending"]
                state["pending"] = False

            if pending:
                log_write(log_file, "[WATCHDOG] Neue Dateien während Run -> starte Folge-Run ...")
                time.sleep(1.0)
                run_pipeline()

    # Initial: falls bereits Dateien da sind -> sofort starten
    try:
        if list_queue_files(paths["in"]):
            log_write(log_file, "[WATCHDOG] Dateien bereits vorhanden -> starte initialen Run ...")
            run_pipeline()
    except Exception as e:
        log_write(log_file, f"[WATCHDOG] Initial-Check Fehler: {e}")

    handler = PickupInHandler(paths["in"], on_trigger=run_pipeline, log_file=log_file, debounce_sec=4.0)
    observer = Observer()
    observer.schedule(handler, str(paths["in"]), recursive=False)
    observer.daemon = True
    observer.start()
    log_write(log_file, "[WATCHDOG] Aktiv. Lege Dateien in PICKUP\\IN, ich starte automatisch.", level="OK")
    log_write(log_file, "[WATCHDOG] Beenden: STRG+C im Fenster. Orca bleibt offen.")

    def _keep_alive_orca(host: str, port: int) -> None:
        """Hält die OrcaScan-Browser-Session durch eine leichte JS-Interaktion am Leben."""
        try:
            from playwright.sync_api import sync_playwright
            endpoint = f"http://{host}:{port}"
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(endpoint)
                for ctx in browser.contexts:
                    for pg in ctx.pages:
                        if "orcascan" in pg.url:
                            pg.evaluate("document.title")
                            log_write(log_file, "[KEEPALIVE] Session aktiv.", level="OK")
                            return
            log_write(log_file, "[KEEPALIVE] Kein OrcaScan-Tab gefunden.", level="WARN")
        except Exception as e:
            log_write(log_file, f"[KEEPALIVE] Fehler: {e}", level="WARN")

    _ka_host, _ka_port = CONFIG["CDP_HOST"], CONFIG["CDP_PORT_START"]
    _ka_counter = 0
    try:
        while True:
            time.sleep(1.0)
            _ka_counter += 1
            if _ka_counter >= 300:  # alle 5 Minuten
                try:
                    _ka_host, _ka_port = ensure_cdp_browser_ready(log_file)
                except Exception:
                    pass
                _keep_alive_orca(_ka_host, _ka_port)
                _ka_counter = 0
    except KeyboardInterrupt:
        log_write(log_file, "[WATCHDOG] Stop (KeyboardInterrupt).")
        set_console_title("Gandalf (gestoppt)")
    finally:
        try:
            observer.stop()
            observer.join(timeout=5)
        except Exception:
            pass
        pause_console("\nWatcher gestoppt. Drücke eine Taste zum Schließen...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\nEs ist ein Fehler aufgetreten:")
        print(e)
        pause_console("\nFehler. Drücke eine Taste zum Schließen...")
