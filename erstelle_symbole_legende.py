# -*- coding: utf-8 -*-
"""
Erstellt eine Symbole-Legende als PDF.
Ausgabe: Desktop/Gandalf_Symbole_Legende.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

OUTPUT = r"C:\Users\Abfuellung 15\Desktop\Gandalf_Symbole_Legende.pdf"  # noqa

W, H = A4  # 595 x 842 pt

c = canvas.Canvas(OUTPUT, pagesize=A4)

# --- Titel ---
c.setFont("Helvetica-Bold", 22)
c.drawString(2*cm, H - 2.5*cm, "Gandalf – Etikett-Symbole")
c.setFont("Helvetica", 11)
c.setFillColor(colors.grey)
c.drawString(2*cm, H - 3.3*cm, "Automatisch gedruckte Symbole je nach Ziel-Kiosk und Zahlungsart")
c.setFillColor(colors.black)

# Trennlinie
c.setStrokeColor(colors.HexColor("#CCCCCC"))
c.setLineWidth(1)
c.line(2*cm, H - 3.8*cm, W - 2*cm, H - 3.8*cm)

# --- Hilfsfunktionen ---
SYM_X   = 3.5*cm   # Symbol-Mitte X
TEXT_X  = 6.5*cm   # Text-Start X
SYM_R   = 0.9*cm   # Symbol-Radius

def draw_row(y_cm, draw_sym_fn, titel, beschreibung, bedingung):
    y = H - y_cm*cm
    # Symbol zeichnen
    draw_sym_fn(y)
    # Titel
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.drawString(TEXT_X, y + 0.3*cm, titel)
    # Bedingung
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(TEXT_X, y - 0.3*cm, bedingung)
    # Beschreibung
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(TEXT_X, y - 0.85*cm, beschreibung)
    c.setFillColor(colors.black)
    # Trennlinie
    c.setStrokeColor(colors.HexColor("#EEEEEE"))
    c.setLineWidth(0.5)
    c.line(2*cm, y - 1.4*cm, W - 2*cm, y - 1.4*cm)


def sym_kreis_voll(y):
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    c.circle(SYM_X, y - 0.2*cm, SYM_R, fill=1, stroke=0)

def sym_ring(y):
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(3)
    c.circle(SYM_X, y - 0.2*cm, SYM_R, fill=0, stroke=1)
    c.setLineWidth(1)

def sym_ausrufe(y):
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    s = SYM_R
    rx = SYM_X - s
    ry = y - 0.2*cm - s
    c.rect(rx, ry, 2*s, 2*s, fill=0, stroke=1)
    c.setLineWidth(1)
    # Strich
    c.setFillColor(colors.black)
    c.rect(SYM_X - 0.1*cm, y - 0.2*cm - 0.1*cm, 0.2*cm, 0.6*cm, fill=1, stroke=0)
    # Punkt
    c.circle(SYM_X, y - 0.2*cm - 0.65*cm, 0.1*cm, fill=1, stroke=0)

# --- Zeilen ---
draw_row(
    y_cm      = 5.5,
    draw_sym_fn = sym_kreis_voll,
    titel     = "Kreis (ausgefüllt)",
    bedingung = "Bedingung: Ziel-Kiosk = Kissel",
    beschreibung = "Paket wird am Kiosk Kissel abgeholt."
)

draw_row(
    y_cm      = 9.0,
    draw_sym_fn = sym_ring,
    titel     = "Ring (Kreis leer)",
    bedingung = "Bedingung: Ziel-Kiosk = Kiosk Mörfelder",
    beschreibung = "Paket wird am Kiosk Mörfelder abgeholt."
)

draw_row(
    y_cm      = 12.5,
    draw_sym_fn = sym_ausrufe,
    titel     = "Ausrufezeichen im Rahmen",
    bedingung = "Bedingung: Zahlung = Vor Ort",
    beschreibung = "Zahlung erfolgt vor Ort beim Abholen."
)

# --- Kombi-Hinweis ---
c.setFont("Helvetica-Bold", 12)
c.setFillColor(colors.black)
c.drawString(2*cm, H - 15.0*cm, "Kombination:")
c.setFont("Helvetica", 10)
c.setFillColor(colors.HexColor("#333333"))
c.drawString(2*cm, H - 15.6*cm, "Wenn zwei Symbole zutreffen, werden sie übereinander gedruckt:")
c.drawString(2*cm, H - 16.1*cm, "  → Kiosk-Symbol oben  |  Zahlungs-Symbol unten")

# --- Fußzeile ---
c.setFont("Helvetica", 8)
c.setFillColor(colors.grey)
c.drawString(2*cm, 1.2*cm, "Gandalf – automatischer Etikettendruck  |  Stand: 02.06.2026")

c.save()
print("PDF erstellt:", OUTPUT)
