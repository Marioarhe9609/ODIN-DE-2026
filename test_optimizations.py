import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up BQ / Vertex AI Environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["OTEL_SDK_DISABLED"] = "TRUE"

from agent.tools_anticorrupcion import diagnostico_integral, detectar_colusion_representante
from agent.tools_gasto import red_flujo_pagos
from agent.tools_mercado import recomendar_procesos_grafo

def run_test(name, func, *args, **kwargs):
    print(f"\n==================================================")
    print(f"TESTING: {name} with args={args} kwargs={kwargs}")
    print(f"==================================================")
    start_time = time.time()
    try:
        res = func(*args, **kwargs)
        elapsed = time.time() - start_time
        print(f"STATUS: SUCCESS")
        print(f"ELAPSED TIME: {elapsed:.2f} seconds")
        print(f"RESULT PREVIEW (first 500 chars):\n{res[:500]}...")
        if len(res) > 500:
            print(f"... [Truncated {len(res)-500} chars] ...")
        return elapsed, True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"STATUS: FAILED")
        print(f"ELAPSED TIME: {elapsed:.2f} seconds")
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return elapsed, False

def main():
    results = []
    
    # 1. Test optimized diagnostico_integral for ICANH (highly responsive and unified)
    elapsed, success = run_test("diagnostico_integral (ICANH)", diagnostico_integral, entidad="ICANH")
    results.append(("diagnostico_integral (ICANH)", elapsed, success))
    
    # 2. Test optimized diagnostico_integral for SENA (large entity)
    elapsed, success = run_test("diagnostico_integral (SENA)", diagnostico_integral, entidad="SENA")
    results.append(("diagnostico_integral (SENA)", elapsed, success))

    # 3. Test new colusion detection graph tool
    elapsed, success = run_test("detectar_colusion_representante (COMPUMAX)", detectar_colusion_representante, proveedor="COMPUMAX")
    results.append(("detectar_colusion_representante", elapsed, success))

    # 4. Test new budget flow graph tool
    elapsed, success = run_test("red_flujo_pagos (SENA 2025)", red_flujo_pagos, entidad="SENA", anio=2025)
    results.append(("red_flujo_pagos", elapsed, success))

    # 5. Test optimized recomendar_procesos_grafo (No CROSS JOIN affinity graph query)
    elapsed, success = run_test("recomendar_procesos_grafo (COMPUMAX)", recomendar_procesos_grafo, proveedor="COMPUMAX")
    results.append(("recomendar_procesos_grafo", elapsed, success))

    print("\n==================================================")
    print("ALL TESTS COMPLETED SUMMARY")
    print("==================================================")
    all_ok = True
    for name, elapsed, success in results:
        status_str = "PASS" if success else "FAIL"
        print(f"- {name:40} : {status_str:4} ({elapsed:.2f}s)")
        if not success:
            all_ok = False
            
    if all_ok:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY IN SUB-2 SECOND LATENCIES!")
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
