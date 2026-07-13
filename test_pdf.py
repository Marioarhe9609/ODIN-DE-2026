"""Test PDF with different response types."""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot.pdf_generator import generate_pdf

TESTS = {
    "budget": ("Ejecucion Presupuestal", """Segun la tabla contratos_electronicos:

**Ejecucion Presupuestal 2025**
*   **Entidad:** UNIDAD PARA LAS VICTIMAS
*   **Presupuesto Asignado:** $101.453 M
*   **Valor Pagado:** $27.364 M
*   **Valor Pendiente de Pago:** $74.088 M
*   **Porcentaje de Ejecucion:** 27%
*   **Numero de Contratos:** 285

**Metodologia:**
- Presupuesto Asignado = SUM(valor_del_contrato)
- Valor Pagado = SUM(valor_pagado)
"""),
    "risk": ("Diagnostico de Riesgo", """**Diagnostico Integral - INVIAS**

[!] MONOPOLIO: 3 proveedores concentran >50% contratos
[!] FRACCIONAMIENTO: 12 contratos fraccionados detectados
[OK] CDP SIN CONTRATO: Sin hallazgos
[!] SOBRECOSTO: 5 contratos con diferencia >30%
[OK] CONTRATACION DIRECTA: Limpia
[!] UNICO PROPONENTE: 8 licitaciones con 1 proponente
[OK] PLAZO MINIMO: Sin hallazgos
[OK] ADICION EXCESIVA: Sin hallazgos
[!] SIN DOCUMENTOS: 15 contratos sin respaldo
[OK] DOCS TARDIOS: Sin hallazgos
"""),
    "ranking": ("Proveedores Monopolistas", """Segun la vista v_anticorr_monopolista:

**Top Proveedores con Concentracion Excesiva**
*   **EMPRESA ABC SAS:** $45.200 M
*   **CONSULTORES XYZ:** $32.800 M
*   **GRUPO DELTA:** $28.500 M
*   **INGENIERIA TOTAL:** $15.300 M
*   **SERVICIOS OMEGA:** $12.100 M
"""),
    "profile": ("Perfil de Contratista", """Segun la tabla contratos_electronicos:

**Perfil del Proveedor NIT 900123456**
*   **Contratos Totales:** 47
*   **Valor Total:** $8.500 M
*   **Contrato Mayor:** $2.300 M
*   **Contrato Menor:** $15 M
*   **Entidades Diferentes:** 12
*   **Departamentos:** 5
"""),
}

desk = os.path.expanduser("~/Desktop")
for name, (title, text) in TESTS.items():
    try:
        path = generate_pdf(text, title)
        size = os.path.getsize(path)
        dest = os.path.join(desk, f"odin_test_{name}.pdf")
        shutil.copy(path, dest)
        print(f"OK {name}: {size:,} bytes -> {dest}")
    except Exception as e:
        print(f"FAIL {name}: {e}")
        import traceback; traceback.print_exc()
