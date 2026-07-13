"""Debug which line causes the PDF crash."""
from fpdf import FPDF
import re

def _safe_text(s):
    emoji_map = {
        "\U0001f534": "[!]", "\U0001f7e0": "[!]", "\U0001f7e1": "[~]", "\U0001f7e2": "[OK]",
        "\U0001f7e3": "[?]", "\u26ab": "[-]", "\U0001f535": "[i]", "\u23f0": "[T]",
        "\U0001f4b0": "[$]", "\u26d4": "[X]", "\u2705": "[OK]", "\u26a0": "[!]",
        "\U0001f536": "[!]", "\U0001f4ca": "[D]", "\U0001f4cb": "[R]", "\U0001f50d": "[S]",
        "\U0001f4c4": "[F]", "\U0001f4ce": "[A]", "\u2b50": "[*]", "\U0001f441": "[O]",
    }
    for em, rep in emoji_map.items():
        s = s.replace(em, rep)
    return s.encode("latin-1", errors="replace").decode("latin-1")

def _clean_md(s):
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)
    s = re.sub(r'\*(.*?)\*', r'\1', s)
    s = re.sub(r'`(.*?)`', r'\1', s)
    return s.strip()

sample = """Según la tabla contratos_electronicos:

**Ejecución Presupuestal 2025**

*   **Entidad:** UNIDAD PARA LAS VÍCTIMAS - FONDO
*   **Ubicación:** Bogotá D.C.
*   **Valor Pagado:** $27.364 M
*   **Porcentaje de Ejecución (Pagado/Asignado):** 27%

📊 **Metodología de Cálculo:**
- Presupuesto Asignado = SUM(valor_del_contrato)
- % Ejecución = (Pagado / Asignado) * 100

🔴 **Alerta:** Ejecución baja del 27%.
"""

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font("Helvetica", "", 9)
pdf.set_y(42)

for i, line in enumerate(sample.split("\n")):
    stripped = line.strip()
    if not stripped:
        pdf.ln(3)
        continue
    
    txt = _safe_text(_clean_md(stripped))
    if not txt.strip():
        continue
    
    print(f"Line {i}: [{txt[:60]}] startswith bullet: {stripped.startswith(('- ', '* ', '  -', '  *'))}")
    
    if stripped.startswith(("- ", "* ", "  -", "  *")):
        bullet_text = "  - " + txt.lstrip("-* ").strip()
        print(f"  -> bullet_text: [{bullet_text[:60]}]")
        try:
            pdf.multi_cell(0, 5, bullet_text)
        except Exception as e:
            print(f"  CRASH at bullet: {e}")
            print(f"  repr: {repr(bullet_text)}")
    else:
        try:
            pdf.multi_cell(0, 5, txt)
        except Exception as e:
            print(f"  CRASH at normal: {e}")
            print(f"  repr: {repr(txt)}")

print("\nDone - no crash!")
pdf.output("test_debug.pdf")
