import json, base64

# Dummy rows
rows = [
    {"representante": f"Rep {i}", "valor_total_adjudicado": 100000, "total_contratos": 2, "empresas_nombres": f"Emp {i}A|Emp {i}B|Emp {i}C"}
    for i in range(5)
]

nodes = {}
edges = []
for r in rows:
    rep_name = "👤 " + (r['representante'][:15] + "..." if len(r['representante']) > 15 else r['representante'])
    if rep_name not in nodes:
        nodes[rep_name] = {"val": r.get('valor_total_adjudicado', 0), "contr": r.get('total_contratos', 0)}
    
    empresas = [e.strip() for e in str(r.get('empresas_nombres', '')).split('|') if e.strip()]
    for emp in empresas:
        emp_name = "🏢 " + (emp[:15] + "..." if len(emp) > 15 else emp)
        if emp_name not in nodes:
            nodes[emp_name] = {"val": 0, "contr": 0}
        edges.append((rep_name, emp_name, 1))

cy_elements = []
for node in nodes.keys():
    val = nodes[node].get('val', 0) or 0
    contr = nodes[node].get('contr', 0)
    color = '#38bdf8'
    size = 30
    val_str = f"${val} COP"
    
    cy_elements.append({
        "data": {
            "id": node,
            "label": node,
            "size": size,
            "color": color,
            "edgecolor": '#334155',
            "val": val_str,
            "contr": f"{contr} contratos"
        }
    })
    
for u, v, w in edges:
    cy_elements.append({
        "data": {
            "id": f"{u}_{v}",
            "source": u,
            "target": v,
            "weight": w,
            "label": f"{w} consorcios"
        }
    })

graph_data_str = json.dumps(cy_elements, ensure_ascii=False, separators=(',', ':'))
graph_data_str = graph_data_str.replace(" ", "").replace("\n", "").replace("\r", "")
encoded_bytes = base64.b64encode(graph_data_str.encode("utf-8"))
encoded_b64 = encoded_bytes.decode("ascii")

print("Nodes:", len(nodes))
print("Edges:", len(edges))
print("JSON length:", len(graph_data_str))
print("Base64 length:", len(encoded_b64))
