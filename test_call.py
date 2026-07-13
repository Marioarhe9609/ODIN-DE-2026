import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.tools_mercado import buscar_contratos

try:
    # This should fail if busqueda has no default value
    res = buscar_contratos(entidad="ICANH", anio=2026)
    print("Direct call succeeded:")
    print(res)
except Exception as e:
    print("Direct call failed with exception:")
    print(e)
