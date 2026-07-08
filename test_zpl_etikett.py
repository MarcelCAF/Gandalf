# -*- coding: utf-8 -*-
"""
Test: Druckt EIN Probe-Etikett per ZPL direkt an den Zebra ZD421.
Layout: Name gross | Barcode-Text | Kiosk unten links | QR-Code rechts.
Etikett: 102 x 38 mm @ 203 dpi (8 dots/mm) -> 816 x 304 dots.
"""
import win32print

PRINTER_NAME = "ZDesigner ZD421-203dpi ZPL"

# Testdaten
NAME = "Alkhatib, Nawaf"
BARCODE = "A-DREZSMZKBT"
KIOSK = "Kissel"


def build_label_zpl(name: str, barcode: str, kiosk: str) -> str:
    return (
        "^XA"
        "^CI28"                                  # UTF-8 (Umlaute)
        "^PW816"                                 # Druckbreite 102mm
        "^LL304"                                 # Etikettenlaenge 38mm
        f"^FO25,54^A0N,55,55^FD{name}^FS"         # Name gross
        f"^FO25,134^A0N,32,32^FD{barcode}^FS"    # Barcode-Text
        f"^FO25,279^A0N,26,26^FD{kiosk}^FS"      # Kiosk klein unten
        f"^FO520,39^BQN,2,9^FDQA,{barcode}^FS"   # QR-Code rechts (+10%)
        "^XZ"
    )


def send_raw_to_printer(printer_name: str, data: bytes) -> None:
    h = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(h, 1, ("Gandalf ZPL Test", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, data)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


if __name__ == "__main__":
    zpl = build_label_zpl(NAME, BARCODE, KIOSK)
    print("Sende an Drucker:", PRINTER_NAME)
    print(zpl)
    send_raw_to_printer(PRINTER_NAME, zpl.encode("utf-8"))
    print("Fertig - Etikett sollte jetzt gedruckt sein.")
