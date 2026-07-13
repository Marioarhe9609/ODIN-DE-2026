import os
os.environ["OTEL_SDK_DISABLED"] = "TRUE"
import agent.tools_mercado

def mock_query(sql, *args, **kwargs):
    print("SQL GENERATED:\n", sql)
    return []

agent.tools_mercado.query = mock_query

res = agent.tools_mercado.analizar_participacion_consorcios(entidad="SENA")
print("RESULT:", res)
