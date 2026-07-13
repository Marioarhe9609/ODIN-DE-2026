"""Odin v2 - Gasto Publico tools for analytics and reporting."""
from agent.bq_client import query, query_view, format_table, safe_like, PROJECT, DATASET


def tabla_ejecucion(entidad: str = "", anio: int = 2025, top: int = 20) -> str:
    """Genera tabla de ejecucion presupuestal: asignado vs pagado vs pendiente
    por entidad. Muestra porcentaje de ejecucion.
    Args:
        entidad: Nombre (parcial) de la entidad. Si vacio, muestra todas.
        anio: Anio a consultar (default: 2025).
        top: Numero maximo de resultados.
    """
    where = f"anio = {anio}"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_gasto_ejecucion_entidad", where=where,
                       order="valor_asignado DESC", limit=top)
    if not rows:
        return f"No se encontraron datos de ejecucion para {anio}."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tabla original SECOP: contratos_electronicos (17M+ contratos adjudicados en SECOP II)\n"
        f"• Vista analitica: v_gasto_ejecucion_entidad\n"
        f"• Filtros aplicados: EXTRACT(YEAR FROM fecha_de_firma) = {anio}, valor_del_contrato > 0"
        + (f", nombre_entidad LIKE '%{entidad}%'" if entidad else "") + "\n"
        f"• SQL de la vista:\n"
        f"  - num_contratos = COUNT(*) agrupado por nombre_entidad y anio\n"
        f"  - valor_asignado = SUM(campo 'valor_del_contrato') — suma de todos los contratos firmados\n"
        f"  - valor_pagado = SUM(campo 'valor_pagado') — campo de SECOP que indica monto ya pagado\n"
        f"  - valor_pendiente = SUM(campo 'valor_pendiente_de_pago') — campo de SECOP con saldo por pagar\n"
        f"  - pct_ejecucion = ROUND(SUM(valor_pagado) * 100 / SUM(valor_del_contrato), 2)\n"
        f"  - valor_facturado = SUM(campo 'valor_facturado') — total facturado segun SECOP\n\n"
    )
    return methodology + f"RESULTADOS ({len(rows)}):\n{format_table(rows)}"


def gasto_por_modalidad(entidad: str = "", anio: int = 2025, top: int = 20) -> str:
    """Muestra como se distribuye el gasto por modalidad de contratacion
    (directa, licitacion, seleccion abreviada, etc.) para una entidad.
    Args:
        entidad: Nombre (parcial) de la entidad.
        anio: Anio a consultar.
        top: Numero maximo de resultados.
    """
    where = f"anio = {anio}"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_gasto_por_modalidad", where=where,
                       order="valor_total DESC", limit=top)
    if not rows:
        return "No se encontraron datos."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tabla original SECOP: contratos_electronicos (dataset 'jbjy-vk9h' de datos.gov.co)\n"
        f"• Vista analitica: v_gasto_por_modalidad\n"
        f"• Filtros: valor_del_contrato > 0, modalidad_de_contratacion NOT NULL, anio = {anio}\n"
        f"• SQL de la vista:\n"
        f"  - num_contratos = COUNT(*) agrupado por modalidad_de_contratacion y nombre_entidad\n"
        f"  - valor_total = SUM(campo 'valor_del_contrato') por modalidad\n"
        f"  - valor_promedio = AVG(campo 'valor_del_contrato') por modalidad\n\n"
    )
    return methodology + f"RESULTADOS:\n{format_table(rows)}"


def tendencia_gasto(entidad: str = "", departamento: str = "", top: int = 24) -> str:
    """Muestra la evolucion mensual del gasto para una entidad o departamento.
    Args:
        entidad: Nombre (parcial) de la entidad.
        departamento: Departamento a filtrar.
        top: Numero de meses a mostrar.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    if departamento:
        where += f" AND LOWER(departamento) LIKE '%{departamento.lower()}%'"
    rows = query_view("v_gasto_temporal", where=where,
                       order="mes DESC", limit=top)
    if not rows:
        return "No se encontraron datos de tendencia."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tabla original SECOP: contratos_electronicos (dataset 'jbjy-vk9h' de datos.gov.co)\n"
        f"• Vista analitica: v_gasto_temporal\n"
        f"• Filtros: fecha_de_firma NOT NULL, valor_del_contrato > 0\n"
        f"• SQL de la vista:\n"
        f"  - mes = FORMAT_TIMESTAMP('%Y-%m', campo 'fecha_de_firma')\n"
        f"  - num_contratos = COUNT(*) agrupado por mes y nombre_entidad\n"
        f"  - valor_total = SUM(campo 'valor_del_contrato') por mes\n\n"
    )
    return methodology + f"RESULTADOS:\n{format_table(rows)}"


def resumen_cdps(entidad: str = "", top: int = 20) -> str:
    """Muestra resumen de Certificados de Disponibilidad Presupuestal (CDPs):
    cuantos tienen contrato, cuantos estan pendientes, montos comprometidos.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND LOWER(entidad) LIKE '%{entidad.lower()}%'"
    rows = query_view("v_gasto_cdps", where=where,
                       order="total_a_comprometer DESC", limit=top)
    if not rows:
        return "No se encontraron datos de CDPs."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tabla original SECOP: solicitudes_cdps (dataset 'a86w-fh92' de datos.gov.co)\n"
        f"• Vista analitica: v_gasto_cdps\n"
        f"• Filtros: entidad NOT NULL\n"
        f"• SQL de la vista:\n"
        f"  - num_cdps = COUNT(*) agrupado por entidad y estado_del_contrato\n"
        f"  - total_a_comprometer = SUM(campo 'saldo_total_a_comprometer')\n"
        f"  - saldo_cdp = SUM(campo 'saldo_cdp')\n"
        f"  - valor_utilizado = SUM(campo 'valor_utilizado')\n"
        f"  - cdps_sin_contrato = COUNT donde id_contrato IS NULL\n\n"
    )
    return methodology + f"RESULTADOS:\n{format_table(rows)}"


def flujo_pagos(entidad: str = "", proveedor: str = "", top: int = 20) -> str:
    """Muestra el flujo de facturacion y pagos por contrato:
    total facturado vs pagado vs pendiente.
    Args:
        entidad: Nombre (parcial) de la entidad.
        proveedor: Nombre (parcial) del proveedor.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    if proveedor:
        where += f" AND LOWER(proveedor_adjudicado) LIKE '%{proveedor.lower()}%'"
    rows = query_view("v_gasto_flujo_pagos", where=where,
                       order="total_facturado DESC", limit=top)
    if not rows:
        return "No se encontraron datos de facturacion."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tablas originales SECOP: facturas ('ibyt-yi2f') JOIN contratos_electronicos ('jbjy-vk9h')\n"
        f"• Se filtran unicamente las facturas con Estado = 'Pagado' para evitar borradores o rechazadas.\n"
        f"• Se agrupa por 'numero_de_factura' para eliminar duplicados de digitacion.\n"
        f"• total_facturado = SUM(valor_total) de facturas unicas pagadas.\n"
        f"• Esta metodologia garantiza que no haya sobrefacturacion irreal (ej. 400%) por errores de SECOP.\n\n"
    )
    return methodology + f"RESULTADOS:\n{format_table(rows)}"


def resumen_compromisos(entidad: str = "", top: int = 20) -> str:
    """Muestra el balance de compromisos presupuestales: comprometido vs
    ejecutado vs liberado por contrato.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_gasto_compromisos", where=where,
                       order="valor_comprometido DESC", limit=top)
    if not rows:
        return "No se encontraron datos de compromisos."
    
    methodology = (
        f"📊 METODOLOGIA DE CALCULO:\n"
        f"• Tablas originales SECOP: compromisos_presupuestales ('skc9-met7') JOIN contratos_electronicos ('jbjy-vk9h')\n"
        f"• Vista analitica: v_gasto_compromisos\n"
        f"• JOIN: compromisos.id_contrato = contratos_electronicos.id_contrato\n"
        f"• SQL de la vista:\n"
        f"  - num_items = COUNT(*) por id_contrato y tipo_de_compromiso\n"
        f"  - valor_comprometido = SUM(campo 'valor_item')\n"
        f"  - balance = SUM(campo 'balance_compromiso')\n"
        f"  - valor_a_liberar = SUM(campo 'valor_a_liberar')\n\n"
    )
    return methodology + f"RESULTADOS:\n{format_table(rows)}"


def red_flujo_pagos(entidad: str, anio: int = 2025, top: int = 15) -> str:
    """Mapea y analiza la red del flujo presupuestal en 3 saltos de SECOP II
    (CDPs solicitado -> Contrato adjudicado -> Facturas pagadas) para una entidad publica.
    Detecta de forma predictiva cuellos de botella y bajas ejecuciones reales.
    Args:
        entidad: Nombre (parcial) de la entidad publica.
        anio: Anio a analizar (default: 2025).
        top: Numero maximo de contratos en la red a mostrar.
    """
    from agent.tools_graficos import generar_red_consorcios
    sql = f"""
    WITH cdps_dedup AS (
        SELECT id_contrato, c_digo_cdp, MAX(SAFE_CAST(saldo_total_a_comprometer AS FLOAT64)) as val
        FROM `{PROJECT}.{DATASET}.solicitudes_cdps`
        WHERE id_contrato IS NOT NULL
        GROUP BY id_contrato, c_digo_cdp
    ),
    facturas_dedup AS (
        SELECT id_contrato, numero_de_factura, MAX(SAFE_CAST(valor_total AS FLOAT64)) as val
        FROM `{PROJECT}.{DATASET}.facturas`
        WHERE id_contrato IS NOT NULL AND (estado = 'Pagado' OR pago_confirmado = 'true')
        GROUP BY id_contrato, numero_de_factura
    )
    SELECT 
      c.id_contrato,
      c.proveedor_adjudicado AS proveedor,
      SUBSTR(c.objeto_del_contrato, 1, 80) AS objeto,
      CAST(c.valor_del_contrato AS INT64) AS valor_contrato,
      COALESCE((SELECT SUM(val) FROM cdps_dedup s WHERE s.id_contrato = c.id_contrato), 0) AS valor_cdps,
      COALESCE((SELECT SUM(val) FROM facturas_dedup f WHERE f.id_contrato = c.id_contrato), 0) AS valor_pagado,
      c.estado_contrato AS estado
    FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
    WHERE {safe_like('c.nombre_entidad', entidad)}
      AND EXTRACT(YEAR FROM c.fecha_de_firma) = {anio}
      AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
    ORDER BY c.valor_del_contrato DESC
    LIMIT {top}
    """
    
    rows = query(sql, max_rows=top)
    
    result = f"=== RED DE FLUJO PRESUPUESTAL (CDPs -> CONTRATO -> PAGOS) ===\n"
    result += f"Entidad: {entidad.upper()} | Año: {anio}\n\n"
    
    if not rows:
        return result + "No se encontraron contratos con flujo presupuestal activo para este año."
        
    # Construir grafo de flujo con generar_red_consorcios
    nodes = {}
    edges = []
    
    # Nodo central de la entidad
    entidad_node = "Entidad"
    nodes[entidad_node] = {"val": sum(r['valor_contrato'] or 0 for r in rows), "contr": len(rows)}
    
    formatted_rows = []
    for r in rows:
        v_contrato = r['valor_contrato'] or 0
        v_cdps = r['valor_cdps'] or 0
        v_pagado = r['valor_pagado'] or 0
        
        pct_ejecucion = (v_pagado * 100 / v_contrato) if v_contrato > 0 else 0.0
        
        prov_name = r['proveedor'][:20] if r['proveedor'] else 'Desconocido'
        # Nodos y conexiones
        if prov_name not in nodes:
            nodes[prov_name] = {"val": 0, "contr": 0}
        nodes[prov_name]["val"] += v_contrato
        nodes[prov_name]["contr"] += 1
        
        edges.append((entidad_node, prov_name, 1))
        
        formatted_rows.append({
            'contrato': r['id_contrato'],
            'proveedor': prov_name,
            'valor_adjudicado': f"${v_contrato:,.0f}",
            'cdps_solicitado': f"${v_cdps:,.0f}",
            'pagos_facturados': f"${v_pagado:,.0f}",
            'ejecucion_real': f"{pct_ejecucion:.1f}%",
            'estado': r['estado']
        })
        
    chart_token = generar_red_consorcios(
        titulo=f"Red de Flujo Presupuestal - {entidad.upper()}",
        central_node=entidad_node,
        nodes=nodes,
        edges=edges
    )
    
    result += f"{chart_token}\n\n"
    result += format_table(formatted_rows) + "\n\n"
    result += "Nota: Este grafo de flujo presupuestal mapea de forma integrada los CDPs de planeacion con la adjudicacion final y el desembolso facturado en tiempo real. Se han corregido las duplicidades inherentes a la estructura de datos abiertos de SECOP II."
    return result


def analizar_presupuesto_paa(entidad: str = "", anio: int = 2025, top: int = 15) -> str:
    """Compara el presupuesto planeado en el PAA contra el ejecutado en contratos.
    Muestra el porcentaje de cumplimiento presupuestal por categoria UNSPSC.
    Args:
        entidad: Nombre o NIT de la entidad publica. Si esta vacio, muestra el listado general de presupuestos.
        anio: Año a analizar (default: 2025).
        top: Numero maximo de categorias/entidades a mostrar.
    """
    if not entidad:
        # General list of top PAA entities by budget
        sql = f"""
        SELECT 
          nombre_entidad,
          nit_entidad,
          COUNT(*) as lineas_planeadas,
          SUM(SAFE_CAST(valor_total_esperado AS FLOAT64)) as presupuesto_planeado
        FROM `{PROJECT}.{DATASET}.plan_anual_adquisiciones`
        WHERE annio = '{anio}'
        GROUP BY nombre_entidad, nit_entidad
        ORDER BY presupuesto_planeado DESC
        LIMIT {top}
        """
        try:
            rows = query(sql, max_rows=top)
        except Exception as err:
            return f"Error al ejecutar el listado del PAA: {err}"
            
        for r in rows:
            r['presupuesto_planeado'] = float(r.get('presupuesto_planeado', 0) or 0)
            r['lineas_planeadas'] = int(r.get('lineas_planeadas', 0) or 0)

        result = f"=== RESUMEN GENERAL DE PLANES ANUALES DE ADQUISICIONES (PAA) - AÑO {anio} ===\n"
        result += "No especificaste una entidad. Mostrando las entidades con mayor presupuesto planeado en el PAA:\n\n"
        
        formatted = []
        for r in rows:
            formatted.append({
                'entidad': r['nombre_entidad'][:40] if r['nombre_entidad'] else '-',
                'nit': r['nit_entidad'] or '-',
                'lineas_paa': r['lineas_planeadas'],
                'presupuesto_planeado': f"${r['presupuesto_planeado']:,.0f}"
            })
        result += format_table(formatted) + "\n\n"
        result += "💡 Sugerencia: Puedes consultar el cumplimiento de una entidad específica diciendo algo como:\n"
        result += f"\"Analizar presupuesto PAA para {rows[0]['nombre_entidad'] if rows else 'SENA'}\""
        return result

    clean = entidad.strip()
    sql_check = f"""
    SELECT DISTINCT nombre_entidad, nit_entidad 
    FROM `{PROJECT}.{DATASET}.plan_anual_adquisiciones`
    WHERE {safe_like('nombre_entidad', clean)} OR nit_entidad = '{clean}'
    LIMIT 1
    """
    ent_rows = query(sql_check)
    if not ent_rows:
        return f"No se encontro el Plan Anual de Adquisiciones (PAA) para '{clean}'."
        
    real_name = ent_rows[0]['nombre_entidad']
    real_nit = ent_rows[0]['nit_entidad']
    
    sql = f"""
    WITH paa_cats AS (
      SELECT 
        SUBSTR(categorias_unspsc, 1, 4) AS cat_prefix,
        SUM(SAFE_CAST(valor_total_esperado AS FLOAT64)) AS planeado,
        COUNT(DISTINCT id_plan_anual_de_adquisiciones) AS lineas_planeadas
      FROM `{PROJECT}.{DATASET}.plan_anual_adquisiciones`
      WHERE nit_entidad = '{real_nit}' AND annio = '{anio}'
      GROUP BY cat_prefix
    ),
    executed_cats AS (
      SELECT 
        SUBSTR(codigo_de_categoria_principal, 1, 4) AS cat_prefix,
        SUM(valor_del_contrato) AS ejecutado,
        COUNT(DISTINCT id_contrato) AS contratos_firmados
      FROM `{PROJECT}.{DATASET}.contratos_electronicos`
      WHERE nit_entidad = '{real_nit}' AND EXTRACT(YEAR FROM fecha_de_firma) = {anio}
      GROUP BY cat_prefix
    ),
    cat_names AS (
      SELECT codigo_familia, ANY_VALUE(nombre_familia) AS nombre_familia
      FROM `{PROJECT}.{DATASET}.unspsc_clasificador`
      GROUP BY codigo_familia
    )
    SELECT 
      p.cat_prefix AS categoria_unspsc,
      COALESCE(c.nombre_familia, 'Otras Categorias') AS descripcion_categoria,
      p.planeado AS valor_planeado,
      p.lineas_planeadas,
      COALESCE(e.ejecutado, 0) AS valor_ejecutado,
      COALESCE(e.contratos_firmados, 0) AS contratos_ejecutados,
      ROUND(COALESCE(e.ejecutado, 0) * 100 / p.planeado, 1) AS pct_ejecucion
    FROM paa_cats p
    LEFT JOIN executed_cats e ON p.cat_prefix = e.cat_prefix
    LEFT JOIN cat_names c ON p.cat_prefix = c.codigo_familia
    WHERE p.planeado > 0
    ORDER BY valor_planeado DESC
    LIMIT {top}
    """
    try:
        rows = query(sql, max_rows=top)
    except Exception as err:
        return f"Error al ejecutar el analisis del PAA: {err}"
        
    for r in rows:
        r['valor_planeado'] = float(r.get('valor_planeado', 0) or 0)
        r['valor_ejecutado'] = float(r.get('valor_ejecutado', 0) or 0)
        r['lineas_planeadas'] = int(r.get('lineas_planeadas', 0) or 0)
        r['contratos_ejecutados'] = int(r.get('contratos_ejecutados', 0) or 0)
        r['pct_ejecucion'] = float(r.get('pct_ejecucion', 0) or 0)
        
    result = f"=== CUMPLIMIENTO DEL PLAN ANUAL DE ADQUISICIONES (PAA) ===\n"
    result += f"Entidad: {real_name} (NIT: {real_nit}) | Año: {anio}\n\n"
    
    if not rows:
        return result + f"No se encontraron registros de planeacion PAA para el año {anio}."
        
    total_planeado = sum(r.get('valor_planeado', 0) for r in rows)
    total_ejecutado = sum(r.get('valor_ejecutado', 0) for r in rows)
    pct_global = (total_ejecutado * 100 / total_planeado) if total_planeado > 0 else 0
    
    result += f"• Presupuesto Planeado Total (Top): ${total_planeado:,.0f} COP\n"
    result += f"• Presupuesto Ejecutado Real: ${total_ejecutado:,.0f} COP\n"
    result += f"• Porcentaje de Ejecucion Global (Top): {pct_global:.1f}%\n\n"
    
    formatted = []
    for r in rows:
        formatted.append({
            'categoria': r['categoria_unspsc'],
            'descripcion': r['descripcion_categoria'],
            'planeado': f"${r['valor_planeado']:,.0f}",
            'lineas': r['lineas_planeadas'],
            'ejecutado': f"${r['valor_ejecutado']:,.0f}",
            'contratos': r['contratos_ejecutados'],
            'cumplimiento': f"{r['pct_ejecucion']}%"
        })
        
    result += format_table(formatted) + "\n\n"
    result += "Nota: Este reporte contrasta las lineas planeadas en el PAA con las adjudicaciones reales en contratos_electronicos agrupadas por divisiones tecnicas UNSPSC."
    return result


def auditar_modificaciones_paa(entidad: str = "", top: int = 15) -> str:
    """Audita las modificaciones sucesivas al PAA de una entidad. 
    Si no se especifica una entidad, muestra las de mayor riesgo en el sistema.
    Activa una alerta si la entidad tiene mas de 5 versiones por año.
    Args:
        entidad: Nombre o NIT de la entidad. Si vacio, muestra las de mayor riesgo global.
        top: Maximo numero de registros a mostrar.
    """
    if entidad:
        clean = entidad.strip()
        where_clause = f"{safe_like('nombre_entidad', clean)} OR nit_entidad = '{clean}'"
        order_clause = "annio DESC, num_versiones DESC"
    else:
        where_clause = "1=1"
        order_clause = "num_versiones DESC, annio DESC"

    sql = f"""
    SELECT 
      nombre_entidad,
      nit_entidad,
      annio,
      num_versiones,
      total_lineas,
      presupuesto_total_planeado,
      ultima_carga
    FROM `{PROJECT}.{DATASET}.v_anticorr_paa_modificaciones`
    WHERE {where_clause}
    ORDER BY {order_clause}
    LIMIT {top}
    """
    rows = query(sql, max_rows=top)
    if not rows:
        if entidad:
            return f"No se encontraron registros de modificaciones del PAA para '{clean}'."
        else:
            return "No se encontraron registros de modificaciones del PAA."
        
    for r in rows:
        r['num_versiones'] = int(r.get('num_versiones', 0) or 0)
        r['total_lineas'] = int(r.get('total_lineas', 0) or 0)
        r['presupuesto_total_planeado'] = float(r.get('presupuesto_total_planeado', 0) or 0)

    result = f"=== AUDITORÍA DE MODIFICACIONES AL PAA ===\n"
    if entidad:
        result += f"Filtro: {entidad}\n\n"
    else:
        result += "Top entidades con mayor número de modificaciones del PAA (Riesgo Alto)\n\n"
    
    formatted = []
    alert_triggered = False
    for r in rows:
        num_v = r['num_versiones']
        status = "🟢 Normal"
        if num_v > 5:
            status = "🚨 ALERTA (>5 cambios)"
            alert_triggered = True
            
        formatted.append({
            'año': r['annio'],
            'entidad': r['nombre_entidad'][:30] if r['nombre_entidad'] else '-',
            'nit': r['nit_entidad'] or '-',
            'versiones': num_v,
            'lineas_paa': r['total_lineas'],
            'presupuesto': f"${r['presupuesto_total_planeado']:,.0f}",
            'alerta': status
        })
        
    result += format_table(formatted) + "\n\n"
    if alert_triggered:
        result += "🚨 ALERTA DE RIESGO DE CORRUPCIÓN: Se detectaron mas de 5 modificaciones anuales al PAA. Las modificaciones sucesivas al plan de compras pueden ser utilizadas para ajustar presupuestos o modalidades a la medida de proveedores preseleccionados antes de abrir las convocatorias oficiales."
    else:
        result += "✅ No se detectaron patrones de modificaciones excesivas al PAA. Nivel de riesgo bajo."
        
    return result


TOOLS = [
    tabla_ejecucion,
    gasto_por_modalidad,
    tendencia_gasto,
    resumen_cdps,
    flujo_pagos,
    resumen_compromisos,
    red_flujo_pagos,
    analizar_presupuesto_paa,
    auditar_modificaciones_paa,
]
