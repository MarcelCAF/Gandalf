"""
test_druck.py
=============
Testet den kompletten Label-Druck-Ablauf in OrcaScan:
1. Verbindet sich per CDP mit dem laufenden Chrome
2. Wählt alle Zeilen aus
3. Klickt Toolbar-Button 'Drucken' -> Dialog 'Etiketten drucken'
4. Wählt 'Custom Label', klickt 'Herunterladen' -> PDF
5. Druckt PDF via SumatraPDF an ZDesigner

VORAUSSETZUNG:
- Chrome läuft mit CDP (Port 9222)
- OrcaScan ist offen (Tab 'Skriptumtopfen' oder 'Tagesbote')
"""

import base64
import io
import subprocess
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import pypdf

# -----------------------------------------------
# KONFIGURATION
# -----------------------------------------------

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

SUMATRA_EXE = r"C:\Users\Abfuellung 15\AppData\Local\SumatraPDF\SumatraPDF.exe"
PRINTER_NAME = "ZDesigner Cannabis 25"

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_PROFILE = str(Path(__file__).parent / "chrome_profile")
ORCA_URL = "https://cloud.orcascan.com/sheets/6936ed1cc6cbc485e4c75d28"

# -----------------------------------------------
# HELPERS
# -----------------------------------------------

def log(msg: str) -> None:
    import datetime
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def ensure_chrome_cdp() -> None:
    """Startet Chrome mit CDP falls noch nicht läuft."""
    import socket
    try:
        with socket.create_connection((CDP_HOST, CDP_PORT), timeout=1):
            log("Chrome mit CDP läuft bereits.")
            return
    except OSError:
        pass

    log("Chrome nicht gefunden – starte Chrome mit CDP...")
    Path(CHROME_PROFILE).mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={CHROME_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        ORCA_URL,
    ])
    # Warte bis CDP erreichbar ist
    for _ in range(20):
        time.sleep(0.5)
        try:
            with socket.create_connection((CDP_HOST, CDP_PORT), timeout=1):
                log("Chrome gestartet.")
                time.sleep(2)  # Seite laden lassen
                return
        except OSError:
            continue
    raise RuntimeError("Chrome konnte nicht gestartet werden (CDP Timeout).")


def find_orca_page(browser):
    """Findet die OrcaScan-Seite im Browser."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "orcascan.com" in pg.url:
                return ctx, pg
    # Fallback: erste Seite
    ctx = browser.contexts[0]
    return ctx, ctx.pages[0]


# -----------------------------------------------
# SCHRITT 1: ZEILEN AUSWÄHLEN
# -----------------------------------------------

def select_all_rows(page) -> int:
    """
    Klickt die 'Alle auswählen' Checkbox im Header.
    Gibt die Anzahl der ausgewählten Zeilen zurück.
    """
    log("Suche 'Alle auswählen' Checkbox...")

    # OrcaScan hat eine Checkbox im Tabellen-Header
    candidates = [
        page.locator("th input[type='checkbox']").first,
        page.locator("thead input[type='checkbox']").first,
        page.locator(".pure-grid-row-header input[type='checkbox']").first,
        page.locator("th.pure-grid-row-header").first,
    ]

    for c in candidates:
        try:
            if c.count() > 0 and c.is_visible(timeout=1000):
                c.click()
                log("  Alle-Auswählen geklickt.")
                page.wait_for_timeout(800)
                break
        except Exception:
            continue
    else:
        log("  WARNUNG: Keine Alle-Auswählen Checkbox gefunden.")
        log("  Bitte Zeilen manuell auswählen und Enter drücken...")
        input("  Enter wenn Zeilen ausgewählt: ")

    # Zähle ausgewählte Zeilen
    count = page.locator("tr.selected, tr[aria-selected='true'], .pure-grid-row.selected").count()
    log(f"  Ausgewählte Zeilen: {count}")
    return count


# -----------------------------------------------
# SCHRITT 2: ETIKETTEN-DIALOG ÖFFNEN
# -----------------------------------------------

def open_label_dialog(page) -> None:
    """
    Öffnet das Etiketten-Seitenpanel (hidden Toggle per Force-Click),
    dann klickt 'Drucken' im Panel -> 'Etiketten drucken' Dialog.
    """
    log("Öffne Etiketten-Seitenpanel...")

    # Toggle ist hidden -> force=True oder JS-Click
    toggle = page.locator("#barcodePreviewOpen")
    try:
        toggle.click(force=True)
        log("  Panel-Toggle geklickt (force).")
    except Exception as e:
        log(f"  Force-Click fehlgeschlagen ({e}), versuche JS...")
        page.evaluate(
            "document.querySelector('#barcodePreviewOpen')"
            " && document.querySelector('#barcodePreviewOpen').click()"
        )

    # Warte bis Seitenpanel sichtbar ist
    panel = page.locator(".barcode-preview-body")
    panel.wait_for(state="visible", timeout=8000)
    log("  Seitenpanel offen.")

    # Drucken-Button im Panel klicken (JS-Click umgeht Viewport-Einschränkungen)
    log("  Klicke 'Drucken' im Etiketten-Panel...")
    print_btn = page.locator("#barcodePreviewForm input[value='Drucken']")
    print_btn.wait_for(state="attached", timeout=5000)
    page.evaluate("document.querySelector('#barcodePreviewForm input[value=\"Drucken\"]').click()")
    log("  Drucken geklickt.")

    # Warte bis Dialog sichtbar ist
    log("  Warte auf Dialog 'Etiketten drucken'...")
    page.locator("div.pure-dialog-title").wait_for(state="visible", timeout=8000)
    log("  Dialog geöffnet.")


# -----------------------------------------------
# SCHRITT 3: ETIKETTENTYP WÄHLEN
# -----------------------------------------------

def select_label_type(page, label_name: str = "Custom Label") -> None:
    """
    Wählt den gewünschten Etikettentyp im Dialog aus.
    Standard: 'Custom Label' (erstes Element, meist schon markiert).
    """
    log(f"  Wähle Etikettentyp: {label_name}")
    try:
        # Suche nur innerhalb des Dialogs (#editDialog)
        dialog = page.locator("#editDialog")
        option = dialog.get_by_text(label_name, exact=False).first
        option.wait_for(state="visible", timeout=3000)
        option.click()
        log("  Etikettentyp ausgewählt.")
    except Exception as e:
        log(f"  WARNUNG: Etikettentyp '{label_name}' nicht gefunden ({e})")
        log("  Verwende was bereits ausgewählt ist.")


# -----------------------------------------------
# SCHRITT 4: HERUNTERLADEN + PDF ABFANGEN
# -----------------------------------------------

def click_download_and_capture(page) -> bytes:
    """
    Klickt 'Herunterladen' im Dialog und fängt den PDF-Download ab.
    Gibt die PDF-Bytes zurück.
    """
    log("Klicke 'Herunterladen' und warte auf PDF-Download...")

    # Eindeutig: Herunterladen-Button im Dialog #editDialog
    herunterladen_btn = page.locator("#editDialog").get_by_role("button", name="Herunterladen")
    herunterladen_btn.wait_for(state="visible", timeout=5000)

    with page.expect_download(timeout=30000) as download_info:
        herunterladen_btn.click()

    download = download_info.value
    log(f"  Download: {download.suggested_filename}")

    # In temporäre Datei speichern und Bytes lesen
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    download.save_as(str(tmp_path))
    pdf_bytes = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)

    log(f"  PDF empfangen: {len(pdf_bytes)} Bytes")
    return pdf_bytes


# -----------------------------------------------
# SCHRITT 5: VIA SUMATRAPDF DRUCKEN
# -----------------------------------------------

def prepare_pdf(pdf_bytes: bytes, target_w_mm: float = 104.0, target_h_mm: float = 38.0) -> bytes:
    """
    Skaliert PDF auf exakte Zielgröße (Querformat, 104 × 38 mm).
    Erstellt eine neue leere Seite in Zielgröße und legt den skalierten
    Originalinhalt hinein – kein Rotate-Flag, kein Mediabox-Chaos.
    ZDesigner muss auf Querformat (104 × 38 mm) eingestellt sein.
    """
    PT_PER_MM = 1.0 / 0.3528  # 1 Punkt = 0.3528 mm
    target_w_pt = target_w_mm * PT_PER_MM   # 104 mm → ~294.7 pt
    target_h_pt = target_h_mm * PT_PER_MM   #  38 mm → ~107.7 pt

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()

    for src_page in reader.pages:
        orig_w = float(src_page.mediabox.width)
        orig_h = float(src_page.mediabox.height)

        # Proportional skalieren damit Inhalt in Zielgröße passt (kein Beschnitt)
        scale = min(target_w_pt / orig_w, target_h_pt / orig_h)
        log(f"  PDF-Skalierung: {orig_w:.1f}×{orig_h:.1f} pt  →  scale={scale:.4f}  →  {orig_w*scale:.1f}×{orig_h*scale:.1f} pt")

        # Neues leeres Blatt in genauer Zielgröße
        new_page = pypdf.PageObject.create_blank_page(
            width=target_w_pt,
            height=target_h_pt,
        )
        # Originalinhalt skaliert auf neues Blatt legen
        transform = Transformation().scale(scale, scale)
        new_page.merge_transformed_page(src_page, transform)

        writer.add_page(new_page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def print_pdf_via_sumatra(pdf_bytes: bytes, printer: str) -> None:
    """Druckt PDF via SumatraPDF lautlos (ohne Dialog)."""
    if not Path(SUMATRA_EXE).exists():
        raise FileNotFoundError(
            f"SumatraPDF nicht gefunden: {SUMATRA_EXE}\n"
            "Bitte Pfad in SUMATRA_EXE anpassen."
        )
    log(f"Drucke via SumatraPDF -> {printer}...")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [SUMATRA_EXE, "-print-to", printer, "-print-settings", "fit,landscape", str(tmp_path)],
            timeout=30,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log("  Druckauftrag gesendet.")
        else:
            log(f"  WARNUNG: SumatraPDF Exit-Code {result.returncode}")
            if result.stderr:
                log(f"  Stderr: {result.stderr}")
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


# -----------------------------------------------
# MAIN
# -----------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  LABEL DRUCK TEST")
    print("=" * 60)

    ensure_chrome_cdp()

    log(f"Verbinde per CDP: {CDP_HOST}:{CDP_PORT}")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{CDP_HOST}:{CDP_PORT}")
        context, page = find_orca_page(browser)

        log(f"Seite: {page.url}")

        # -- Schritt 1: Zeilen auswählen --
        select_all_rows(page)

        # -- Schritt 2: Etiketten-Dialog öffnen --
        open_label_dialog(page)

        # -- Schritt 3: Etikettentyp wählen --
        select_label_type(page, label_name="ZDesignerPU")

        # -- Schritt 4: Herunterladen + PDF abfangen --
        pdf_bytes = click_download_and_capture(page)

        # PDF zur Kontrolle speichern
        debug_pdf = Path(__file__).parent / "debug_labels.pdf"
        debug_pdf.write_bytes(pdf_bytes)
        log(f"  Debug-PDF gespeichert: {debug_pdf}")

        # -- Schritt 5: Drucken (SumatraPDF skaliert automatisch) --
        print_pdf_via_sumatra(pdf_bytes, PRINTER_NAME)

        log("Fertig!")

    print("\n" + "=" * 60)
    input("Enter zum Beenden...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    except Exception as e:
        print(f"\nFEHLER: {e}")
        import traceback
        traceback.print_exc()
        input("\nEnter zum Beenden...")
