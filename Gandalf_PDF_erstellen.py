"""
Gandalf_PDF_erstellen.py
Erzeugt die Arbeitsanweisung als formatierte PDF im CAF-Stil.
Benoetigt: pip install fpdf2
"""

from fpdf import FPDF
from pathlib import Path
from datetime import datetime

# --- Pfade ---
SCRIPT_DIR = Path(__file__).parent
LOGO_PATH = Path(r"C:\Users\Abfuellung 15\Pictures\caflogo.png")
OUTPUT_PDF = SCRIPT_DIR / "Gandalf_Arbeitsanweisung.pdf"

# --- Farben (CAF-Gruen) ---
GREEN = (74, 137, 60)
GREEN_LIGHT = (230, 243, 225)
GREEN_DARK = (45, 90, 35)
WHITE = (255, 255, 255)
BLACK = (40, 40, 40)
GRAY = (100, 100, 100)
GRAY_LIGHT = (245, 245, 245)
GRAY_LINE = (200, 200, 200)


class GandalfPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        self.is_cover = False

    def header(self):
        if self.is_cover:
            return
        # Gruene Kopfleiste
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*WHITE)
        self.set_xy(10, 3)
        self.cell(0, 6, "Gandalf - Arbeitsanweisung", align="R")
        self.set_text_color(*BLACK)
        self.set_y(18)

    def footer(self):
        if self.is_cover:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 10, "Cannabis Apotheke Frankfurt  |  Internes Dokument", align="L")
        self.cell(0, 10, f"Seite {self.page_no()}/{{nb}}", align="R")

    def add_cover_page(self):
        self.is_cover = True
        self.add_page()

        # Gruener Balken oben
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 50, "F")

        # Skriptname im Balken
        self.set_font("Helvetica", "B", 36)
        self.set_text_color(*WHITE)
        self.set_xy(15, 10)
        self.cell(0, 16, "Gandalf", ln=True)
        self.set_font("Helvetica", "", 14)
        self.set_xy(15, 28)
        self.cell(0, 10, "Automatischer OrcaScan-Import mit QR-Label-Druck")

        # Logo
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=55, y=65, w=100)

        # Titel
        self.set_text_color(*BLACK)
        self.set_font("Helvetica", "B", 28)
        self.set_xy(15, 120)
        self.cell(0, 14, "Arbeitsanweisung", ln=True, align="C")
        self.set_font("Helvetica", "", 14)
        self.set_text_color(*GRAY)
        self.set_xy(15, 138)
        self.cell(0, 10, "Bedienung und Funktionsbeschreibung", align="C", ln=True)

        # Gruene Trennlinie
        self.set_draw_color(*GREEN)
        self.set_line_width(1)
        self.line(60, 155, 150, 155)

        # Info-Box
        self.set_y(165)
        self.set_fill_color(*GREEN_LIGHT)
        self.set_draw_color(*GREEN)
        self.rect(40, 165, 130, 45, "DF")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*GREEN_DARK)
        self.set_xy(45, 170)
        self.cell(120, 8, "Cannabis Apotheke Frankfurt", align="C", ln=True)
        self.set_xy(45, 180)
        self.cell(120, 8, f"Stand: {datetime.now().strftime('%d.%m.%Y')}", align="C", ln=True)
        self.set_xy(45, 190)
        self.cell(120, 8, "Version 1.0", align="C", ln=True)

        # Gruener Balken unten
        self.set_fill_color(*GREEN)
        self.rect(0, 275, 210, 22, "F")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*WHITE)
        self.set_xy(15, 280)
        self.cell(180, 8, "Internes Dokument  --  Cannabis Apotheke Frankfurt  --  Kissel Apotheke", align="C")

        self.is_cover = False

    def section_header(self, number, title):
        self.ln(6)
        if self.get_y() > 260:
            self.add_page()
        # Gruener Hintergrund
        y = self.get_y()
        self.set_fill_color(*GREEN)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 13)
        self.rect(10, y, 190, 10, "F")
        self.set_xy(12, y + 1)
        self.cell(0, 8, f"{number}. {title}")
        self.set_text_color(*BLACK)
        self.ln(14)

    def sub_header(self, title):
        if self.get_y() > 265:
            self.add_page()
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*GREEN_DARK)
        self.cell(0, 8, title, ln=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def hint_box(self, text, icon=""):
        y = self.get_y()
        if y > 260:
            self.add_page()
            y = self.get_y()
        self.set_fill_color(255, 248, 220)
        self.set_draw_color(220, 190, 80)
        self.set_font("Helvetica", "I", 9)
        lines = self.multi_cell(180, 5, f"{icon} {text}", dry_run=True, output="LINES")
        box_h = len(lines) * 5 + 6
        self.rect(10, y, 190, box_h, "DF")
        self.set_xy(15, y + 3)
        self.multi_cell(180, 5, f"{icon} {text}")
        self.ln(4)

    def code_block(self, text):
        y = self.get_y()
        if y > 255:
            self.add_page()
            y = self.get_y()
        self.set_fill_color(*GRAY_LIGHT)
        self.set_draw_color(*GRAY_LINE)
        self.set_font("Courier", "", 8.5)
        lines = text.strip().split("\n")
        box_h = len(lines) * 4.5 + 6
        self.rect(12, y, 186, box_h, "DF")
        self.set_xy(15, y + 3)
        for line in lines:
            self.cell(0, 4.5, line, ln=True)
            self.set_x(15)
        self.ln(4)

    def add_table(self, headers, rows, col_widths=None):
        if self.get_y() > 250:
            self.add_page()

        if col_widths is None:
            n = len(headers)
            col_widths = [190 / n] * n

        # Header
        self.set_fill_color(*GREEN)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_text_color(*BLACK)
        self.set_font("Helvetica", "", 8.5)
        alt = False
        for row in rows:
            if alt:
                self.set_fill_color(*GRAY_LIGHT)
            else:
                self.set_fill_color(*WHITE)
            alt = not alt

            # Calculate max height for this row
            max_lines = 1
            for i, cell in enumerate(row):
                lines = self.multi_cell(col_widths[i], 5, str(cell), dry_run=True, output="LINES")
                max_lines = max(max_lines, len(lines))

            row_h = max_lines * 5
            if self.get_y() + row_h > 280:
                self.add_page()
                # Repeat header
                self.set_fill_color(*GREEN)
                self.set_text_color(*WHITE)
                self.set_font("Helvetica", "B", 9)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
                self.ln()
                self.set_text_color(*BLACK)
                self.set_font("Helvetica", "", 8.5)
                if alt:
                    self.set_fill_color(*GRAY_LIGHT)
                else:
                    self.set_fill_color(*WHITE)

            y_start = self.get_y()
            for i, cell in enumerate(row):
                x = self.get_x() if i == 0 else sum(col_widths[:i]) + 10
                self.set_xy(x, y_start)
                self.multi_cell(col_widths[i], 5, str(cell), border=1, fill=True)
            self.set_y(y_start + row_h)

        self.ln(4)

    def simple_table(self, headers, rows, col_widths=None):
        """Simpler table using single-line cells only."""
        if self.get_y() > 250:
            self.add_page()

        if col_widths is None:
            n = len(headers)
            col_widths = [190 / n] * n

        # Header
        self.set_fill_color(*GREEN)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_text_color(*BLACK)
        self.set_font("Helvetica", "", 8.5)
        alt = False
        for row in rows:
            if self.get_y() > 275:
                self.add_page()
                # Repeat header
                self.set_fill_color(*GREEN)
                self.set_text_color(*WHITE)
                self.set_font("Helvetica", "B", 9)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
                self.ln()
                self.set_text_color(*BLACK)
                self.set_font("Helvetica", "", 8.5)

            if alt:
                self.set_fill_color(*GRAY_LIGHT)
            else:
                self.set_fill_color(*WHITE)
            alt = not alt

            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell), border=1, fill=True)
            self.ln()

        self.ln(4)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        x_start = self.l_margin
        self.set_x(x_start)
        self.cell(8, 5.5, "  -  ", new_x="END")
        self.multi_cell(0, 5.5, text)

    def numbered_item(self, num, text):
        x_start = self.l_margin
        self.set_x(x_start)
        self.set_font("Helvetica", "B", 10)
        self.cell(10, 5.5, f" {num}. ", new_x="END")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)


def build_pdf():
    pdf = GandalfPDF()
    pdf.alias_nb_pages()

    # ========================
    # DECKBLATT
    # ========================
    pdf.add_cover_page()

    # ========================
    # INHALT
    # ========================

    # --- 1. Voraussetzungen ---
    pdf.add_page()
    pdf.section_header(1, "Voraussetzungen")
    pdf.simple_table(
        ["Anforderung", "Detail"],
        [
            ["Python", "3.10 oder neuer"],
            ["Bibliotheken", "pandas, openpyxl, watchdog, playwright"],
            ["Installation (einmalig)", "PIPpin.bat ausfuehren"],
            ["Browser", "Google Chrome (wird automatisch gestartet)"],
            ["Drucker", "ZDesigner ZD421-203dpi (Standarddrucker)"],
            ["Netzlaufwerk", "W:\\Dokumentenaustausch\\... muss erreichbar sein"],
        ],
        col_widths=[55, 135],
    )
    pdf.body_text("Das Skript liegt im Ordner: Marcels Skripts\\Gandalf\\Gandalf.py")

    # --- 2. Ordnerstruktur ---
    pdf.section_header(2, "Ordnerstruktur")
    pdf.body_text("Gandalf arbeitet mit einer festen Ordnerstruktur unterhalb von PICKUP:")
    pdf.simple_table(
        ["Ordner", "Zweck"],
        [
            ["PICKUP\\IN", "Eingabeordner - hier werden die Dateien abgelegt"],
            ["PICKUP\\OUT", "Ausgabe - zusammengefuehrte Datei orca_tagesboten.xlsx"],
            ["PICKUP\\ARCHIVE", "Archiv - erfolgreich verarbeitete Dateien"],
            ["PICKUP\\ERROR", "Fehlerordner - fehlerhafte Dateien"],
            ["PICKUP\\logs", "Log-Dateien - pro Tag eine Datei"],
        ],
        col_widths=[45, 145],
    )
    pdf.hint_box("Alle Ordner werden beim Start automatisch erstellt, falls sie noch nicht existieren.")

    # --- 3. Programmstart ---
    pdf.section_header(3, "Programmstart")
    pdf.body_text("Doppelklick auf Gandalf.py (oder ueber die Kommandozeile: python Gandalf.py).")
    pdf.body_text("Das Programm oeffnet ein Konsolenfenster und zeigt:")
    pdf.code_block("Gandalf Watcher gestartet\nBaseDir=W:\\Dokumentenaustausch\\Tagesskripte\\PICKUP\nUeberwache: W:\\...\\PICKUP\\IN\n[WATCHDOG] Aktiv. Lege Dateien in PICKUP\\IN, ich starte automatisch.")
    pdf.body_text("Gandalf ueberwacht nun dauerhaft den Ordner PICKUP\\IN.")
    pdf.hint_box("Wichtig: Das Konsolenfenster muss offen bleiben! Zum Beenden: STRG+C druecken.")

    # --- 4. Ablauf ---
    pdf.section_header(4, "Ablauf - Schritt fuer Schritt")
    pdf.body_text("Sobald Dateien in PICKUP\\IN abgelegt werden, startet Gandalf automatisch:")

    pdf.sub_header("Schritt 1: Datei erkennen und einlesen")
    pdf.bullet("Gandalf erkennt automatisch das Quellformat (BW, CAF oder WAWICAN)")
    pdf.bullet("CSV- und Excel-Dateien werden unterstuetzt")
    pdf.bullet("Die Datei wird in ein einheitliches OrcaScan-Format umgewandelt")
    pdf.ln(3)

    pdf.sub_header("Schritt 2: Zusammenfuehren (Merge)")
    pdf.bullet("Mehrere Dateien im IN-Ordner werden zusammengefuehrt")
    pdf.bullet("Ergebnis wird als orca_tagesboten.xlsx in PICKUP\\OUT gespeichert")
    pdf.bullet("Originaldateien werden nach PICKUP\\ARCHIVE verschoben")
    pdf.ln(3)

    pdf.sub_header("Schritt 3: Upload in OrcaScan")
    pdf.bullet("Chrome-Browser wird automatisch mit OrcaScan geoeffnet")
    pdf.bullet("Die zusammengefuehrte Datei wird in den Tab \"Tagesbote\" importiert")
    pdf.bullet("Drei Import-Dialoge werden automatisch bestaetigt")
    pdf.ln(3)

    pdf.sub_header("Schritt 4: QR-Labels drucken")
    pdf.bullet("Neu importierte Zeilen werden automatisch selektiert")
    pdf.bullet("Das Etiketten-Panel wird geoeffnet")
    pdf.bullet("QR-Labels werden an den Standarddrucker gesendet")
    pdf.ln(3)

    pdf.sub_header("Schritt 5: Warten auf neue Dateien")
    pdf.body_text("Nach Abschluss wartet Gandalf wieder auf neue Dateien. Der Vorgang wiederholt sich automatisch.")

    # --- 5. Dateiformate ---
    pdf.section_header(5, "Unterstuetzte Dateiformate")
    pdf.body_text("Gandalf erkennt drei verschiedene Quellformate automatisch anhand der Spaltenkoepfe:")

    # BW
    pdf.sub_header("Bloomwell (BW)")
    pdf.body_text("Dateityp: CSV (Semikolon-getrennt)")
    pdf.simple_table(
        ["Quellspalte (BW)", "Zielspalte (OrcaScan)"],
        [
            ["OrderNumber", "Paket-Barcode"],
            ["DateOfOrder", "Datum"],
            ["Shipping_LastName + FirstName", "Name"],
            ["Pharmacy", "Ziel-Kiosk"],
            ["Status", "Status"],
            ["Total", "Bestellwert"],
            ["DeliveryOption", "Lieferung"],
            ["PaymentStatus", "Zahlung"],
        ],
        col_widths=[95, 95],
    )
    pdf.hint_box("Filter: Nur Bestellungen mit DeliveryOption = pickup werden exportiert.")

    # CAF
    pdf.sub_header("Cannabis Apotheke Frankfurt (CAF)")
    pdf.body_text("Dateityp: CSV (Komma-getrennt)")
    pdf.simple_table(
        ["Quellspalte (CAF)", "Zielspalte (OrcaScan)"],
        [
            ["Best.-Nr.", "Paket-Barcode"],
            ["Datum", "Datum"],
            ["Name", "Name"],
            ["(leer)", "Ziel-Kiosk"],
            ["Status", "Status"],
            ["Bestellwert", "Bestellwert"],
            ["Versicher.", "Versicher."],
            ["Lieferung", "Lieferung"],
            ["Zahlung", "Zahlung"],
        ],
        col_widths=[95, 95],
    )
    pdf.hint_box("Filter: Nur Bestellungen mit Lieferung = pickup werden exportiert.")

    # WAWICAN
    pdf.sub_header("WAWICAN")
    pdf.body_text("Dateityp: XLSX (Excel mit eingebetteten CSV-Daten)")
    pdf.simple_table(
        ["Quellspalte (WAWICAN)", "Zielspalte (OrcaScan)"],
        [
            ["Id", "Paket-Barcode"],
            ["Reservierungsdatum", "Datum"],
            ["Nachname + Vorname", "Name"],
            ["Abholort", "Ziel-Kiosk (autom. umbenannt)"],
            ["Status", "Status"],
            ["Rechnungsbetrag", "Bestellwert"],
            ["Versichertenstatus", "Versicher."],
            ["Lieferart", "Lieferung"],
            ["vor Ort Zahlung", "Zahlung"],
        ],
        col_widths=[95, 95],
    )

    pdf.sub_header("Ziel-Kiosk-Zuordnung (WAWICAN)")
    pdf.simple_table(
        ["Abholort (enthaelt)", "Wird zu"],
        [
            ["Ernst-Wiss-Str. 9 / MadVapes Griesheim", "Ernst"],
            ["Leipziger Str. 20 / Kissel Apotheke", "Kissel"],
            ["Ostbahnhofstr. 18 / MadVapes Ostbahnhof", "Ost"],
            ["Moerfelder Landstr. 225/245", "Kiosk Moerfelder"],
        ],
        col_widths=[120, 70],
    )

    # --- 6. Erster Start / Login ---
    pdf.section_header(6, "OrcaScan - Erster Start und Login")
    pdf.body_text("Beim allerersten Start oeffnet Gandalf einen neuen Chrome-Browser mit eigenem Profil (getrennt vom normalen Chrome).")
    pdf.ln(2)
    pdf.bold_text("Einmalig noetig:")
    pdf.numbered_item(1, "Gandalf startet und oeffnet Chrome mit OrcaScan")
    pdf.numbered_item(2, "Im Log erscheint: \"Button 'Importieren' nicht sichtbar - vermutlich nicht eingeloggt.\"")
    pdf.numbered_item(3, "Im geoeffneten Chrome-Fenster: Bei OrcaScan manuell einloggen")
    pdf.numbered_item(4, "Gandalf erkennt den Login automatisch und faehrt fort")
    pdf.numbered_item(5, "Ab dem naechsten Start ist man bereits eingeloggt")
    pdf.ln(3)
    pdf.hint_box("Wichtig: Das Chrome-Fenster, das Gandalf oeffnet, darf NICHT geschlossen werden! Es bleibt im Hintergrund offen und wird fuer jeden Import wiederverwendet.")

    # --- 7. QR-Label-Druck ---
    pdf.section_header(7, "QR-Label-Druck")
    pdf.body_text("Der automatische Label-Druck erfolgt nach jedem erfolgreichen Import:")
    pdf.ln(1)
    pdf.numbered_item(1, "Gandalf merkt sich die Zeilenzahl VOR dem Import")
    pdf.numbered_item(2, "Nach dem Import wird die NEUE Zeilenzahl gelesen")
    pdf.numbered_item(3, "Die Differenz ergibt die neu importierten Zeilen")
    pdf.numbered_item(4, "Diese Zeilen werden in OrcaScan selektiert (gelb markiert)")
    pdf.numbered_item(5, "Das Etiketten-Panel wird geoeffnet (rechte Seitenleiste)")
    pdf.numbered_item(6, "\"Drucken\" wird geklickt")
    pdf.numbered_item(7, "Der Dialog \"Etiketten drucken\" wird bestaetigt")
    pdf.numbered_item(8, "Die Labels werden an den Standarddrucker gesendet")
    pdf.ln(3)
    pdf.hint_box("Voraussetzung: Der ZDesigner ZD421-203dpi muss als Windows-Standarddrucker eingerichtet sein.")
    pdf.body_text("Label-Druck deaktivieren: In der Konfiguration (Zeile PRINT_LABELS_AFTER_IMPORT) auf False setzen.")

    # --- 8. Konfiguration ---
    pdf.section_header(8, "Konfiguration")
    pdf.body_text("Die wichtigsten Einstellungen befinden sich am Anfang der Datei Gandalf.py im Bereich CONFIG:")
    pdf.simple_table(
        ["Einstellung", "Standard", "Beschreibung"],
        [
            ["ORCA_SHEET_TAB_NAME", "Tagesbote", "Name des OrcaScan-Tabs"],
            ["PRINT_LABELS_AFTER_IMPORT", "True", "QR-Labels autom. drucken"],
            ["BW_EXPORT_ONLY_PICKUP", "True", "Nur Pickup-Bestellungen (BW)"],
            ["CAF_EXPORT_ONLY_PICKUP", "True", "Nur Pickup-Bestellungen (CAF)"],
            ["CLEANUP_DAYS", "14", "Alte Logs/Archive loeschen nach X Tagen"],
            ["BASE_PICKUP_DIR", "W:\\...\\PICKUP", "Hauptverzeichnis"],
        ],
        col_widths=[65, 40, 85],
    )

    # --- 9. Log-Dateien ---
    pdf.section_header(9, "Log-Dateien")
    pdf.body_text("Gandalf schreibt automatisch Log-Dateien in den Ordner PICKUP\\logs. Pro Tag wird eine Datei erstellt (z.B. run__watch__20260219.log).")
    pdf.ln(1)
    pdf.body_text("Jede Zeile hat einen Zeitstempel und eine Kategorie:")
    pdf.simple_table(
        ["Kategorie", "Bedeutung"],
        [
            ["[INFO]", "Normaler Ablauf"],
            ["[OK]", "Erfolgreiche Aktion"],
            ["[WARN]", "Warnung (Skript laeuft weiter)"],
            ["[ERR]", "Fehler (Aktion abgebrochen, Skript laeuft weiter)"],
        ],
        col_widths=[40, 150],
    )
    pdf.body_text("Beispiel-Log:")
    pdf.code_block("[2026-02-19 09:14:19] [INFO] Queue: Cannabis Apotheke_... .csv\n[2026-02-19 09:14:21] [INFO] Erkannt: CAF | ORCA-Zeilen: 1\n[2026-02-19 09:14:38] [INFO] Import abgeschlossen.\n[2026-02-19 09:14:50] [OK]   QR-Labels gedruckt: 1 Etiketten.")
    pdf.body_text("Alte Log-Dateien werden automatisch nach 14 Tagen geloescht (einstellbar ueber CLEANUP_DAYS).")

    # --- 10. Haeufige Fehler ---
    pdf.section_header(10, "Haeufige Fehler und Loesungen")
    pdf.simple_table(
        ["Fehlermeldung", "Ursache", "Loesung"],
        [
            ["BASE_PICKUP_DIR nicht erreichbar", "Netzlaufwerk W: nicht verbunden", "Netzlaufwerk verbinden, neu starten"],
            ["Button 'Importieren' nicht sichtbar", "Nicht bei OrcaScan eingeloggt", "Im Chrome-Fenster manuell einloggen"],
            ["Zeilenzahl nicht auslesbar", "OrcaScan nicht geladen", "Skript neu starten"],
            ["Etiketten-Panel nicht oeffenbar", "OrcaScan-UI geaendert", "Skript neu starten, Marcel kontaktieren"],
            ["FEHLER beim Label-Druck", "Drucker nicht erreichbar", "Drucker pruefen, Standarddrucker setzen"],
            ["watchdog nicht installiert", "Python-Bibliothek fehlt", "pip install watchdog"],
            ["CSV nicht einlesbar", "Unbekanntes Format", "Datei in PICKUP\\ERROR pruefen"],
            ["Chrome nicht gefunden", "Chrome nicht installiert", "Google Chrome installieren"],
            ["Fehlende Spalten: [...]", "Falsche Spaltenkoepfe", "Dateiformat pruefen (Abschnitt 5)"],
        ],
        col_widths=[60, 55, 75],
    )

    # --- 11. Tagesablauf ---
    pdf.section_header(11, "Tagesablauf - Kurzanleitung")
    pdf.ln(2)
    pdf.numbered_item(1, "Morgens: Doppelklick auf Gandalf.py - das Konsolenfenster oeffnet sich")
    pdf.ln(2)
    pdf.numbered_item(2, "Tagsuebers: CSV- oder Excel-Dateien in PICKUP\\IN ablegen (per Download, Kopieren etc.)")
    pdf.ln(2)
    pdf.numbered_item(3, "Gandalf erledigt den Rest: Import + QR-Druck laufen vollautomatisch")
    pdf.ln(2)
    pdf.numbered_item(4, "Abends: Konsolenfenster mit STRG+C schliessen (optional - Gandalf kann auch dauerhaft laufen)")
    pdf.ln(4)
    pdf.hint_box("Tipp: Mehrere Dateien koennen gleichzeitig in den IN-Ordner gelegt werden. Gandalf wartet kurz (4 Sekunden) und verarbeitet dann alle auf einmal.")

    # --- PDF speichern ---
    pdf.output(str(OUTPUT_PDF))
    print(f"PDF erstellt: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
