"""Odin v2 - Tienda Virtual del Estado Colombiano (TVEC) tools."""
from agent.bq_client import query, query_view, format_table, safe_like, PROJECT, DATASET

T = f"`{PROJECT}.{DATASET}"


def analizar_compras_tienda_virtual(entidad: str, anio: int = 2025, top: int = 15) -> str:
    """Muestra un resumen de las compras de una entidad publica en la Tienda Virtual (TVEC).
    Muestra las categorias (acuerdos marco) mas compradas y los principales proveedores.
    Args:
        entidad: Nombre o NIT de la entidad.
        anio: Año de las compras (default: 2025).
        top: Numero maximo de resultados a mostrar.
    """
    clean = entidad.strip()
    sql_check = f"""
    SELECT DISTINCT entidad, nit_entidad 
    FROM `{PROJECT}.{DATASET}.tienda_virtual_consolidado`
    WHERE {safe_like('entidad', clean)} OR nit_entidad = '{clean}'
    LIMIT 1
    """
    ent_rows = query(sql_check)
    if not ent_rows:
        return f"No se encontraron registros de transacciones en la Tienda Virtual (TVEC) para '{clean}'."
        
    real_name = ent_rows[0]['entidad']
    real_nit = ent_rows[0]['nit_entidad']
    
    # Query categories/aggregations
    sql_cats = f"""
    SELECT 
      agregacion AS categoria,
      COUNT(DISTINCT identificador_de_la_orden) AS ordenes,
      SUM(CAST(total AS INT64)) AS valor_total
    FROM `{PROJECT}.{DATASET}.tienda_virtual_consolidado`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}') AND a_o = '{anio}'
    GROUP BY categoria
    ORDER BY valor_total DESC
    LIMIT {top}
    """
    
    # Query top providers in TVEC
    sql_provs = f"""
    SELECT 
      proveedor,
      nit_proveedor,
      COUNT(DISTINCT identificador_de_la_orden) AS ordenes,
      SUM(CAST(total AS INT64)) AS valor_total
    FROM `{PROJECT}.{DATASET}.tienda_virtual_consolidado`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}') AND a_o = '{anio}'
    GROUP BY proveedor, nit_proveedor
    ORDER BY valor_total DESC
    LIMIT 5
    """
    
    cats_rows = query(sql_cats)
    provs_rows = query(sql_provs)
    
    result = f"=== REPORTE DE COMPRAS EN TIENDA VIRTUAL (TVEC) ===\n"
    result += f"Entidad: {real_name} (NIT: {real_nit}) | Año: {anio}\n\n"
    
    if not cats_rows:
        return result + f"No se registraron ordenes de compra en la Tienda Virtual para el año {anio}."
        
    total_gasto = sum(r.get('valor_total', 0) or 0 for r in cats_rows)
    total_orders = sum(r.get('ordenes', 0) or 0 for r in cats_rows)
    
    result += f"• Gasto Total Registrado (Top): ${total_gasto:,.0f} COP\n"
    result += f"• Total de Ordenes de Compra (Top): {total_orders}\n\n"
    
    result += "📊 DISTRIBUCIÓN POR ACUERDOS MARCO / CATEGORÍAS:\n"
    formatted_cats = []
    for r in cats_rows:
        formatted_cats.append({
            'acuerdo_marco': r['categoria'][:40],
            'ordenes': r['ordenes'],
            'valor_compras': f"${r['valor_total']:,.0f}"
        })
    result += format_table(formatted_cats) + "\n\n"
    
    result += "👤 TOP 5 PROVEEDORES EN LA TIENDA VIRTUAL:\n"
    formatted_provs = []
    for r in provs_rows:
        formatted_provs.append({
            'proveedor': r['proveedor'][:30],
            'nit': r['nit_proveedor'],
            'ordenes': r['ordenes'],
            'valor_compras': f"${r['valor_total']:,.0f}"
        })
    result += format_table(formatted_provs) + "\n\n"
    
    return result


def auditar_riesgo_tienda_virtual(entidad: str, top: int = 15) -> str:
    """Evalua y reporta las 4 banderas rojas de la Tienda Virtual (TVEC) para una entidad:
    1. Monopolio en Acuerdos Marco (concentracion >70% y valor >20M)
    2. Fraccionamiento de Ordenes (multiples compras en 5 dias al mismo proveedor)
    3. Raspado de Olla (gasto excesivo en diciembre >40%)
    4. Compras con NIT no definidos (falta de transparencia, valor >50M)
    Args:
        entidad: Nombre o NIT de la entidad.
        top: Numero maximo de alertas a mostrar.
    """
    clean = entidad.strip()
    
    # Look up correct name/NIT
    sql_check = f"""
    SELECT DISTINCT entidad, nit_entidad 
    FROM `{PROJECT}.{DATASET}.tienda_virtual_consolidado`
    WHERE {safe_like('entidad', clean)} OR nit_entidad = '{clean}'
    LIMIT 1
    """
    ent_rows = query(sql_check)
    if not ent_rows:
        return f"No se encontraron transacciones de la Tienda Virtual (TVEC) para '{clean}'."
        
    real_name = ent_rows[0]['entidad']
    real_nit = ent_rows[0]['nit_entidad']
    
    result = f"=== AUDITORÍA DE RIESGO EN TIENDA VIRTUAL (TVEC) ===\n"
    result += f"Entidad: {real_name} (NIT: {real_nit})\n\n"
    
    alertas_activas = []
    
    # 1. Monopolio / Concentracion
    sql_monop = f"""
    SELECT agregacion, proveedor, nit_proveedor, valor_proveedor, valor_total_categoria, pct_concentracion_valor
    FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_monopolio`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}') AND pct_concentracion_valor > 70 AND valor_total_categoria > 20000000
    ORDER BY pct_concentracion_valor DESC
    LIMIT 3
    """
    monop_rows = query(sql_monop)
    if monop_rows:
        msg = "🚨 ALERTA: Concentración Excesiva en Acuerdos Marco (Monopolio TVEC):\n"
        for r in monop_rows:
            msg += f"  - En '{r['agregacion'][:30]}' el proveedor '{r['proveedor'][:30]}' concentra el {r['pct_concentracion_valor']}% del gasto (${r['valor_proveedor']:,.0f} de ${r['valor_total_categoria']:,.0f} en total).\n"
        alertas_activas.append(msg)
        
    # 2. Fraccionamiento
    sql_frac = f"""
    SELECT proveedor, nit_proveedor, num_ordenes_cercanas, valor_total_sumado, ordenes_fraccionadas
    FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_fraccionamiento`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}')
    ORDER BY num_ordenes_cercanas DESC, valor_total_sumado DESC
    LIMIT 3
    """
    frac_rows = query(sql_frac)
    if frac_rows:
        msg = "🚨 ALERTA: Posible Fraccionamiento de Órdenes en TVEC:\n"
        for r in frac_rows:
            msg += f"  - El proveedor '{r['proveedor'][:30]}' recibió {r['num_ordenes_cercanas']} órdenes de compra en un lapso menor a 5 días, sumando ${r['valor_total_sumado']:,.0f} COP (Órdenes: {r['ordenes_fraccionadas']}).\n"
        alertas_activas.append(msg)
        
    # 3. Raspado de olla (Gasto en Diciembre)
    sql_rasp = f"""
    SELECT anio, valor_diciembre, valor_anual, pct_gasto_diciembre
    FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_raspado_olla`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}') AND pct_gasto_diciembre > 40
    ORDER BY anio DESC
    LIMIT 3
    """
    rasp_rows = query(sql_rasp)
    if rasp_rows:
        msg = "🚨 ALERTA: Gasto Acelerado de Fin de Año ('Raspado de Olla' en TVEC):\n"
        for r in rasp_rows:
            msg += f"  - En el año {r['anio']}, se gastó el {r['pct_gasto_diciembre']}% del presupuesto anual de TVEC solo en el mes de diciembre (${r['valor_diciembre']:,.0f} de ${r['valor_anual']:,.0f} total).\n"
        alertas_activas.append(msg)
        
    # 4. Falta de Transparencia (NITs invalidos/no aplicables)
    sql_trans = f"""
    SELECT a_o, identificador_de_la_orden, proveedor, total
    FROM `{PROJECT}.{DATASET}.tienda_virtual_consolidado`
    WHERE (entidad = '{real_name}' OR nit_entidad = '{real_nit}') 
      AND (nit_proveedor IN ('No Aplica', 'No Definido', '') OR nit_proveedor IS NULL)
      AND CAST(total AS INT64) > 50000000
    ORDER BY total DESC
    LIMIT 3
    """
    trans_rows = query(sql_trans)
    if trans_rows:
        msg = "🚨 ALERTA: Órdenes de Alta Cuantía sin Identificación de Proveedor (Falta de Transparencia):\n"
        for r in trans_rows:
            v = float(r.get('total', 0) or 0)
            msg += f"  - Orden {r['identificador_de_la_orden']} ({r['a_o']}) por ${v:,.0f} COP adjudicada a '{r['proveedor'][:30]}' sin NIT registrado.\n"
        alertas_activas.append(msg)
        
    # Build final response
    if alertas_activas:
        for a in alertas_activas:
            result += a + "\n"
        result += "*(Estas alertas analizan patrones inusuales en las órdenes de compra emitidas en la Tienda Virtual del Estado Colombiano que podrían vulnerar los principios de transparencia y libre concurrencia).* "
    else:
        result += "✅ No se detectaron alertas de riesgo ni patrones atípicos de compra en la Tienda Virtual (TVEC) para esta entidad."
        
    return result


TOOLS = [
    analizar_compras_tienda_virtual,
    auditar_riesgo_tienda_virtual,
]
