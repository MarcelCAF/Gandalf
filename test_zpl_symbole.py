# -*- coding: utf-8 -*-
"""
Testdruck: Symbole übereinander wenn beide gleichzeitig.
1) Kissel + Vor Ort    -> Kreis voll (oben) + Ausrufezeichen (unten)
2) Mörfelder + Vor Ort -> Ring (oben)        + Ausrufezeichen (unten)
3) Kissel allein       -> Kreis voll zentriert (Kontrolle)
4) Vor Ort allein      -> Ausrufezeichen zentriert (Kontrolle)
"""
import win32print

PRINTER_NAME = "ZDesigner ZD421-203dpi ZPL"

BASE = (
    "^XA^CI28^PW816^LL304"
    "^FO25,54^A0N,55,55^FD{name}^FS"
    "^FO25,134^A0N,32,32^FD{barcode}^FS"
    "^FO25,279^A0N,26,26^FD{kiosk}^FS"
    "^FO520,39^BQN,2,9^FDQA,{barcode}^FS"
    "{symbol}"
    "^XZ"
)

# Symbole einzeln (zentriert, Y=136)
KREIS_VOLL_EINZEL  = "^FO368,136^GE80,80,80,B^FS"
RING_EINZEL        = "^FO368,136^GE80,80,7,B^FS"
AUSRUFE_EINZEL     = ("^FO368,136^GB80,80,5^FS"
                      "^FO400,154^GB12,32,12^FS"
                      "^FO400,199^GB12,12,12^FS")

# Symbole übereinander: Kiosk oben Y=81, Zahlung unten Y=191
KREIS_VOLL_OBEN    = "^FO368,81^GE80,80,80,B^FS"
RING_OBEN          = "^FO368,81^GE80,80,7,B^FS"
AUSRUFE_UNTEN      = ("^FO368,191^GB80,80,5^FS"
                      "^FO400,209^GB12,32,12^FS"
                      "^FO400,254^GB12,12,12^FS")

etiketten = [
    {"name": "Alkhatib, Nawaf", "barcode": "A-TEST0001", "kiosk": "Kissel",
     "symbol": KREIS_VOLL_OBEN + AUSRUFE_UNTEN, "label": "1/4 Kissel + Vor Ort"},
    {"name": "Alkhatib, Nawaf", "barcode": "A-TEST0002", "kiosk": "Kiosk Mörfelder",
     "symbol": RING_OBEN + AUSRUFE_UNTEN,        "label": "2/4 Mörfelder + Vor Ort"},
    {"name": "Alkhatib, Nawaf", "barcode": "A-TEST0003", "kiosk": "Kissel",
     "symbol": KREIS_VOLL_EINZEL,                "label": "3/4 Kissel allein"},
    {"name": "Alkhatib, Nawaf", "barcode": "A-TEST0004", "kiosk": "Kissel",
     "symbol": AUSRUFE_EINZEL,                   "label": "4/4 Vor Ort allein"},
]

h = win32print.OpenPrinter(PRINTER_NAME)
try:
    for e in etiketten:
        zpl = BASE.format(**e)
        win32print.StartDocPrinter(h, 1, (e["label"], None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, zpl.encode("utf-8"))
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
        print("Gedruckt:", e["label"])
finally:
    win32print.ClosePrinter(h)
print("Fertig!")
