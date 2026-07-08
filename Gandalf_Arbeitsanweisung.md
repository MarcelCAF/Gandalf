# GANDALF – Arbeitsanweisung

**Automatischer PU-Import & Etikettendruck**

- **Zugehöriges Skript:** `Gandalf.py`
- **Datum:** 10. Juni 2026
- **Erstellt für:** Apothekenmitarbeiter

---

## Inhalt

1. [Überblick](#1-überblick)
2. [Voraussetzungen & Einmaleinrichtung](#2-voraussetzungen--einmaleinrichtung)
3. [Gandalf starten](#3-gandalf-starten)
4. [Normaler Ablauf (Schritt für Schritt)](#4-normaler-ablauf-schritt-für-schritt)
5. [Unterstützte Dateiformate](#5-unterstützte-dateiformate)
6. [Etikettendruck (ZPL)](#6-etikettendruck-zpl)
7. [Etikett-Symbole](#7-etikett-symbole)
8. [Ordnerstruktur](#8-ordnerstruktur)
9. [Logs & Fehlermeldungen](#9-logs--fehlermeldungen)
10. [Häufige Fragen (FAQ)](#10-häufige-fragen-faq)

---

## 1. Überblick

Gandalf ist ein **automatischer Hintergrund-Wächter**: Er überwacht einen Ordner auf dem NAS und verarbeitet neue Bestelldateien vollständig automatisch – ohne dass man etwas klicken muss.

**Was Gandalf tut (in dieser Reihenfolge):**

1. Neue Datei im `IN`-Ordner erkennen
2. Format erkennen (BW, CAF oder WAWICAN)
3. Daten bereinigen und zusammenführen
4. In OrcaScan (Tagesboten-Sheet) importieren
5. Datensätze in die Abholer_DB übertragen (Name, Barcode, Ziel-Kiosk, Bestellwert, Zahlungsart …)
6. Etiketten direkt auf dem Zebra-Drucker ausdrucken (ZPL)
7. Verarbeitete Datei ins Archiv verschieben

> **Fachbegriffe kurz erklärt:**
> - **PU** = Pickup-Auftrag (ein Paket, das abgeholt werden soll)
> - **NAS** = das gemeinsame Netzlaufwerk `W:\`
> - **OrcaScan** = das Scan-System (Tagesboten-Sheet = Liste der heutigen Pakete)
> - **Abholer_DB** = OrcaScan-Datenbank mit allen Abholer-Daten (Name, Status, Zeitstempel)
> - **ZPL** = Drucksprache des Zebra-Druckers (Etiketten werden direkt gesendet, kein PDF nötig)
> - **CDP** = Verbindung zu einem im Hintergrund laufenden Chrome-Browser

---

## 2. Voraussetzungen & Einmaleinrichtung

Diese Punkte müssen **einmalig** pro PC eingerichtet sein, bevor Gandalf läuft.

### 2.1 Netzlaufwerk

Das NAS muss unter **`W:\`** erreichbar sein.
Prüfen: Windows Explorer → `W:\Dokumentenaustausch\Tagesskripte\PICKUP` muss existieren.

### 2.2 Chrome (detached) laufend

Gandalf steuert OrcaScan über einen Chrome-Browser, der **im Hintergrund läuft** (nicht sichtbar). Dieser Browser muss vor dem Gandalf-Start geöffnet und in OrcaScan **eingeloggt** sein.

Zum Starten des Hintergrund-Browsers:

```
PICKUP\start_detached_chrome.bat
```

> ⚠️ Wenn Chrome nicht läuft oder nicht in OrcaScan eingeloggt ist, schlägt der Import fehl.

### 2.3 Python-Pakete

Einmalig im Terminal installieren (falls noch nicht vorhanden):

```
pip install pandas openpyxl playwright watchdog pywin32 requests
playwright install chromium
```

Das Paket **`pywin32`** wird für den ZPL-Direktdruck benötigt. Ohne es werden keine Etiketten gedruckt (Gandalf läuft aber trotzdem weiter).

### 2.4 Zebra-Drucker

- Drucker **„ZDesigner Cannabis 28"** muss als Windows-Drucker installiert sein (USB oder Netzwerk).
- Ist der Drucker unter einem anderen Namen installiert → in `Gandalf.py` unter `LABEL_ZPL_PRINTER` anpassen.

---

## 3. Gandalf starten

```
Doppelklick auf: PICKUP\start_gandalf.bat
```

Oder direkt im Terminal:

```
python Gandalf.py
```

Gandalf startet und zeigt in der Konsole:

```
[OK]  Watchdog läuft. Ordner wird überwacht: W:\...\PICKUP\IN
[OK]  Warte auf neue Dateien …
```

Gandalf läuft jetzt **dauerhaft im Hintergrund**. Das Fenster offen lassen (minimieren ist OK). Zum Beenden: `Strg+C`.

### Session Keep-Alive

Alle **5 Minuten** schickt Gandalf automatisch einen kleinen „Ping" an den OrcaScan-Browser-Tab, damit die Sitzung nicht abläuft. Im Log erscheint dann:

```
[OK]  [KEEPALIVE] Session aktiv.
```

---

## 4. Normaler Ablauf (Schritt für Schritt)

### Schritt 1 – Datei in IN-Ordner legen

Bestelldatei (von BW, CAF oder WAWICAN exportiert) in diesen Ordner kopieren:

```
W:\Dokumentenaustausch\Tagesskripte\PICKUP\IN\
```

Das ist alles, was der Mitarbeiter tun muss. Gandalf übernimmt ab hier automatisch.

### Schritt 2 – Gandalf erkennt die Datei

Sobald die Datei vollständig gespeichert ist (~2 Sekunden), erkennt Gandalf sie und startet die Verarbeitung. Im Log:

```
[INFO] Neue Datei erkannt: bestellung_heute.xlsx
[INFO] Format erkannt: BW
```

### Schritt 3 – Import in OrcaScan

Gandalf öffnet den OrcaScan-Tab im Hintergrund-Browser und importiert die Zeilen in das **Tagesboten-Sheet**.

```
[OK]  Import abgeschlossen: 14 Zeilen importiert.
```

### Schritt 4 – Eintrag in Abholer_DB

Gleichzeitig werden alle Pakete per API direkt in die **Abholer_DB** übertragen:

- Name, Barcode, Ziel-Kiosk, Zahlungsart, Bestellwert
- Status wird auf „Verpackt" gesetzt (Zeitstempel = jetzt)

```
[OK]  Abholer_DB: 14 Einträge geschrieben.
```

### Schritt 5 – Etikettendruck

Die Etiketten für alle verarbeiteten Pakete werden sofort auf dem **Zebra-Drucker** ausgedruckt:

```
[OK]  [ZPL] 14 Etiketten gedruckt.
```

### Schritt 6 – Datei archivieren

Die verarbeitete Datei wird aus `IN` in den `ARCHIVE`-Ordner verschoben:

```
W:\...\PICKUP\ARCHIVE\20260610-143022_bestellung_heute.xlsx
```

Bei einem Fehler landet sie stattdessen im `ERROR`-Ordner.

---

## 5. Unterstützte Dateiformate

Gandalf erkennt drei Export-Formate automatisch:

| Format | Erkennungsmerkmal | Dateiart |
|---|---|---|
| **BW** (Bloomwell) | Spalten `OrderNumber`, `Shipping_LastName` | CSV oder Excel |
| **CAF** (Cannabis Apotheke Frankfurt) | Spalten `Best.-Nr.`, `Lieferung` | CSV oder Excel |
| **WAWICAN** | Spalte `Reservierungsdatum` vorhanden | CSV oder Excel |

> ℹ️ Nur Pakete mit Abhol-Typ „pickup" werden verarbeitet. Lieferungen werden herausgefiltert.

### Spalten-Zuordnung: BW

| Quellspalte (BW) | Zielspalte (OrcaScan) |
|---|---|
| `OrderNumber` | Paket-Barcode |
| `DateOfOrder` | Datum |
| `Shipping_LastName, Shipping_FirstName` | Name |
| `Pharmacy` | Ziel-Kiosk |
| `Total` | Bestellwert |
| `PaymentStatus` | Zahlung |

### Spalten-Zuordnung: CAF

| Quellspalte (CAF) | Zielspalte (OrcaScan) |
|---|---|
| `Best.-Nr.` | Paket-Barcode |
| `Datum` | Datum |
| `Name` | Name |
| `Bestellwert` | Bestellwert |
| `Zahlung` | Zahlung |

### Spalten-Zuordnung: WAWICAN

| Quellspalte (WAWICAN) | Zielspalte (OrcaScan) |
|---|---|
| `Id` | Paket-Barcode |
| `Reservierungsdatum` | Datum |
| `Nachname, Vorname` | Name |
| `Abholort` | Ziel-Kiosk (automatisch umbenannt, siehe unten) |
| `Rechnungsbetrag` | Bestellwert |
| `vor Ort Zahlung` + `Zahlungsstatus` | Zahlung |

**Ziel-Kiosk-Zuordnung WAWICAN** (Abholort wird automatisch übersetzt):

| Abholort enthält … | Wird zu |
|---|---|
| Ernst-Wiss-Straße 9 / MadVapes Griesheim | Ernst |
| Kissel Apotheke / Leipziger Str. 20 | Kissel |
| Ostbahnhofstraße 18 / MadVapes Ostbahnhof | Ost |
| Mörfelder Landstr. 225 oder 245 / Mörfelders | Kiosk Mörfelder |

**Zahlungsart „Vor Ort" bei WAWICAN** wird aus zwei Spalten kombiniert:
- Ist `vor Ort Zahlung` = Ja → **Vor Ort**
- Ist `Zahlungsstatus` leer oder „Rechnung versendet" → **Vor Ort**
- Sonst → **Erhalten**

---

## 6. Etikettendruck (ZPL)

Die Etiketten werden **direkt** an den Zebra-Drucker ZD421 gesendet – ohne PDF, ohne SumatraPDF, ohne Browser-Umweg. Das ist schneller und zuverlässiger.

### Etikett-Layout (102 × 38 mm)

```
┌────────────────────────────────────────────────────┐
│ Müller, Klaus                    [             ]   │
│                                  [   QR-Code   ]   │
│ A-DREZSMZKBT                     [             ]   │
│                                  [ Symbol ggf. ]   │
│ Kissel                                             │
└────────────────────────────────────────────────────┘
```

- **Oben links:** Name des Empfängers (Schriftgröße passt sich automatisch an)
- **Mitte links:** Paket-Barcode (Text)
- **Unten links:** Ziel-Kiosk
- **Rechts:** QR-Code (Inhalt = Paket-Barcode, für Scannen)
- **Rechts Mitte:** Symbol (wenn zutreffend, siehe Abschnitt 7)

### Dynamische Schriftgröße

Bei langen Namen wird der Text automatisch kleiner, damit er nicht in den QR-Code hineinragt:

| Namenslänge | Schriftgröße |
|---|---|
| bis 15 Zeichen | groß (55 pt) |
| bis 22 Zeichen | mittel (42 pt) |
| über 22 Zeichen | klein (35 pt) |

Wenn zusätzlich **Symbole** gedruckt werden, gelten strengere Schwellenwerte (bis auf 28 pt Minimum bei sehr langen Namen).

---

## 7. Etikett-Symbole

Bestimmte Pakete bekommen automatisch ein **Symbol** auf dem Etikett, damit Mitarbeiter Ziel-Kiosk und Zahlungsart auf einen Blick erkennen.

| Symbol | Aussehen | Bedingung |
|---|---|---|
| **Kreis (ausgefüllt)** | ● | Ziel-Kiosk = **Kissel** |
| **Ring (Kreis leer)** | ○ | Ziel-Kiosk = **Kiosk Mörfelder** |
| **Ausrufezeichen im Rahmen** | ▣ | Zahlung = **Vor Ort** |

### Zwei Symbole gleichzeitig

Treffen Kiosk-Symbol und Zahlungs-Symbol gleichzeitig zu, werden sie **übereinander** gedruckt:

- **Oben:** Kiosk-Symbol (Kreis oder Ring)
- **Unten:** Zahlungs-Symbol (Ausrufezeichen im Rahmen)

---

## 8. Ordnerstruktur

```
W:\Dokumentenaustausch\Tagesskripte\PICKUP\
│
├── IN\          ← Hier neue Dateien hineinlegen (Eingabe)
├── OUT\         ← Zusammengeführte Exportdatei (orca_tagesboten.xlsx)
├── ARCHIVE\     ← Erfolgreich verarbeitete Dateien
├── ERROR\       ← Fehlgeschlagene Dateien
└── logs\        ← Tägliche Log-Dateien (run__watch__YYYYMMDD.log)
```

> ℹ️ Logs und Archiv-Dateien, die älter als **14 Tage** sind, werden automatisch gelöscht.

---

## 9. Logs & Fehlermeldungen

Gandalf schreibt alle Meldungen sowohl in die Konsole als auch in eine Log-Datei:

```
W:\...\PICKUP\logs\run__watch__20260610.log
```

### Log-Level

| Level | Farbe | Bedeutung |
|---|---|---|
| `[OK]` | Grün | Schritt erfolgreich abgeschlossen |
| `[INFO]` | Normal | Normaler Fortschritt |
| `[WARN]` | Gelb | Warnung – Gandalf macht weiter, aber etwas stimmt nicht |
| `[ERR]` | Rot | Fehler – dieser Schritt ist fehlgeschlagen |

### Häufige Fehlermeldungen

| Meldung | Ursache | Lösung |
|---|---|---|
| `Kein OrcaScan-Tab gefunden` | Chrome nicht gestartet oder nicht eingeloggt | `start_detached_chrome.bat` ausführen, in OrcaScan einloggen |
| `[ZPL] pywin32 nicht installiert` | Python-Paket fehlt | `pip install pywin32` im Terminal ausführen |
| `[ZPL] Drucker nicht gefunden` | Drucker nicht installiert oder falscher Name | Drucker in Windows installieren / Namen in Gandalf.py prüfen |
| `Datei wird noch geschrieben` | Datei wurde noch nicht vollständig gespeichert | Gandalf wartet automatisch – kein Handlungsbedarf |
| Datei landet in `ERROR\` | Import- oder API-Fehler | Log öffnen, Fehlermeldung lesen; Datei ggf. erneut in `IN` legen |
| `BASE_PICKUP_DIR nicht erreichbar` | Netzlaufwerk `W:\` nicht verbunden | Netzlaufwerk verbinden, Gandalf neu starten |

---

## 10. Häufige Fragen (FAQ)

**Muss ich Gandalf jeden Tag neu starten?**
Nein. Gandalf läuft dauerhaft weiter. Nur nach einem PC-Neustart muss Gandalf (und der Hintergrund-Chrome) neu gestartet werden.

**Was passiert, wenn ich dieselbe Datei versehentlich zweimal in IN lege?**
Gandalf verarbeitet sie ein zweites Mal. In OrcaScan werden Duplikate ggf. doppelt angelegt. Daher bitte jede Datei nur einmal hineinkopieren.

**Etiketten wurden nicht gedruckt – was tun?**
Log prüfen (Abschnitt 9). Häufigste Ursachen: Drucker aus, USB-Kabel, falscher Druckername. Etiketten lassen sich nicht automatisch nachdrucken – ggf. manuell in OrcaScan drucken.

**Die OrcaScan-Sitzung ist abgelaufen – was tun?**
Chrome-Fenster (läuft im Hintergrund) öffnen und manuell bei OrcaScan einloggen. Gandalf verbindet sich beim nächsten Import automatisch wieder. Dank des Keep-Alive (alle 5 Minuten) sollte das selten passieren.

**Eine Datei liegt im ERROR-Ordner – was tun?**
1. Log-Datei des gleichen Tages öffnen (`logs\run__watch__YYYYMMDD.log`).
2. Fehlermeldung lesen und Ursache beheben.
3. Datei aus `ERROR` in `IN` zurücklegen – Gandalf versucht es erneut.
4. Falls der Fehler bleibt: Marcel informieren.

**Kann Gandalf auf mehreren PCs gleichzeitig laufen?**
Ja – aber der Zebra-Drucker ist immer nur an einem PC angeschlossen. Auf dem PC ohne Drucker werden Etiketten übersprungen (kein Fehler, nur eine Warnung im Log).

**Welche Dateiformate werden nicht akzeptiert?**
Nur `.csv`, `.xlsx`, `.xls`. PDF, Word und andere Formate werden ignoriert und nicht in den ERROR-Ordner verschoben.

**Wie erkenne ich, ob Gandalf läuft?**
Das Konsolenfenster mit dem Titel „Gandalf" ist offen. Im Fenster steht `[WATCHDOG] Aktiv.` oder es erscheinen regelmäßig `[KEEPALIVE]`-Meldungen.

**Warum steht im Log „0 Etiketten gedruckt"?**
Wenn nach dem Import keine neuen Zeilen in OrcaScan erkannt wurden (z. B. weil alle Barcodes schon vorhanden waren), gibt es nichts zu drucken. Das ist kein Fehler.

---

*Diese Arbeitsanweisung beschreibt den Stand von Gandalf vom 10. Juni 2026. Bei Änderungen am Skript können Details abweichen.*
