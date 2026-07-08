# -*- coding: utf-8 -*-
"""
Druckt ein Übersichts-Etikett mit allen nativen ZPL-Formen.
102 x 38mm @ 203dpi
"""
import win32print

PRINTER_NAME = "ZDesigner ZD421-203dpi ZPL"

zpl = (
    "^XA"
    "^CI28"
    "^PW816"
    "^LL304"

    # --- Titel ---
    "^FO10,5^A0N,20,20^FDFormen-Uebersicht^FS"

    # --- Zeile 1: Ausgefuellte Kreise (verschiedene Groessen) ---
    "^FO10,35^A0N,18,18^FDKreis:^FS"
    "^FO90,38^GE40,40,40,B^FS"     # ausgefuellter Kreis klein (Ellipse)
    "^FO145,43^GE30,30,30,B^FS"    # Kreis mittel
    "^FO190,48^GE20,20,20,B^FS"    # Kreis klein

    # --- Zeile 2: Nur Rahmen (Kreise) ---
    "^FO10,90^A0N,18,18^FDRing:^FS"
    "^FO90,93^GE40,40,3,B^FS"      # Kreis nur Rahmen (duenn)
    "^FO145,93^GE40,40,6,B^FS"     # Kreis Rahmen (mittel)
    "^FO195,93^GE40,40,12,B^FS"    # Kreis Rahmen (dick)

    # --- Zeile 3: Rechtecke ausgefuellt ---
    "^FO10,148^A0N,18,18^FDBlock:^FS"
    "^FO90,148^GB50,25,25^FS"      # Rechteck ausgefuellt
    "^FO155,150^GB70,20,20^FS"     # Rechteck breit
    "^FO240,148^GB25,25,25^FS"     # Quadrat

    # --- Zeile 4: Rechteck nur Rahmen ---
    "^FO10,190^A0N,18,18^FDRahmen:^FS"
    "^FO90,190^GB50,30,2^FS"       # Rahmen duenn
    "^FO155,190^GB50,30,5^FS"      # Rahmen mittel
    "^FO220,190^GB50,30,10^FS"     # Rahmen dick

    # --- Zeile 5: Diagonale Linien ---
    "^FO10,238^A0N,18,18^FDLinie:^FS"
    "^FO90,238^GD50,30,3,B,R^FS"   # Linie rechts-unten
    "^FO155,238^GD50,30,3,B,L^FS"  # Linie links-unten

    # --- Rechte Seite: Kombinationen (moegliche Icons) ---
    # Haken (Checkmark) aus Linien
    "^FO580,40^A0N,18,18^FDOK:^FS"
    "^FO580,65^GB60,60,4^FS"        # Rahmen
    "^FO590,88^GD15,20,4,B,R^FS"   # kurze Linie
    "^FO605,108^GD35,35,4,B,L^FS"  # lange Linie

    # Ausrufezeichen
    "^FO690,40^A0N,18,18^FD!:^FS"
    "^FO690,65^GB60,60,4^FS"        # Rahmen
    "^FO715,75^GB10,30,10^FS"       # Strich
    "^FO715,115^GB10,10,10^FS"      # Punkt

    "^XZ"
)

import win32print
h = win32print.OpenPrinter(PRINTER_NAME)
try:
    win32print.StartDocPrinter(h, 1, ("ZPL Formen Test", None, "RAW"))
    win32print.StartPagePrinter(h)
    win32print.WritePrinter(h, zpl.encode("utf-8"))
    win32print.EndPagePrinter(h)
    win32print.EndDocPrinter(h)
finally:
    win32print.ClosePrinter(h)
print("Etikett gedruckt!")
