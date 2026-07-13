"""Odin v2 - Anticorrupcion tools for the ADK agent."""
from agent.bq_client import query, query_view, format_table, safe_like, strip_accents, PROJECT, DATASET, JUNK_FILTER_SQL

T = f"`{PROJECT}.{DATASET}"


def buscar_proveedor_monopolista(entidad: str = "", top: int = 20) -> str:
    """Busca proveedores que concentran un porcentaje anormalmente alto de contratos
    en una misma entidad publica. Indica posible direccionamiento de contratos.
    Args:
        entidad: Nombre (parcial) de la entidad a analizar. Si vacio, busca en todas.
        top: Numero maximo de resultados.
    """
    where = f"pct_contratos_entidad > 50"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_monopolista", where=where,
                       order="pct_contratos_entidad DESC", limit=top)
    if not rows:
        return f"No se encontraron proveedores monopolistas para '{entidad}'."
    return f"Proveedores con concentracion excesiva:\n{format_table(rows)}"


def detectar_fraccionamiento(entidad: str = "", mes: str = "", top: int = 20) -> str:
    """Detecta posible fraccionamiento de contratos: multiples contratos de minima cuantia
    al mismo proveedor que sumados superarian el umbral de licitacion publica.
    Args:
        entidad: Nombre (parcial) de la entidad.
        mes: Mes en formato YYYY-MM (ej: 2025-03).
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    if mes:
        where += f" AND mes = '{mes}'"
    rows = query_view("v_anticorr_fraccionamiento", where=where,
                       order="valor_total_sumado DESC", limit=top)
    if not rows:
        return "No se detectaron patrones de fraccionamiento."
    return f"Posible fraccionamiento detectado:\n{format_table(rows)}"


def buscar_sin_competencia(entidad: str = "", top: int = 20) -> str:
    """Busca procesos competitivos (Licitacion, Seleccion Abreviada, etc)
    que solo tuvieron UN proponente y ademas se adjudicaron por el 100% 
    del presupuesto, sugiriendo pliegos sastre.
    NOTA: Excluye contratos con precio_base <= 1000000 (placeholders).
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "SAFE_CAST(precio_base AS FLOAT64) > 1000000"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_sin_competencia", where=where,
                       order="precio_base DESC", limit=top)
    if not rows:
        return "No se encontraron licitaciones sin competencia."
    return f"Procesos competitivos con un solo proponente:\n{format_table(rows)}"


def buscar_proveedor_sancionado(proveedor: str = "", top: int = 20) -> str:
    """Busca proveedores que tienen sanciones o multas y aun asi recibieron
    contratos posteriores a la fecha de la sancion.
    Args:
        proveedor: Nombre o NIT del proveedor (parcial).
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if proveedor:
        where += f" AND (LOWER(proveedor_sancionado) LIKE '%{proveedor.lower()}%' OR nit_sancionado = '{proveedor}')"
    rows = query_view("v_anticorr_sancionado_activo", where=where,
                       order="valor_del_contrato DESC", limit=top)
    if not rows:
        return "No se encontraron proveedores sancionados con contratos activos."
    return f"Proveedores sancionados con contratos posteriores:\n{format_table(rows)}"


def buscar_adiciones_excesivas(entidad: str = "", min_adiciones: int = 3, top: int = 20) -> str:
    """Busca contratos con un numero excesivo de adiciones (de valor o plazo),
    que pueden indicar mala planeacion o manipulacion del contrato original.
    Args:
        entidad: Nombre (parcial) de la entidad.
        min_adiciones: Minimo de adiciones para considerar excesivo (default: 3).
        top: Numero maximo de resultados.
    """
    where = f"num_adiciones >= {min_adiciones}"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_adiciones", where=where,
                       order="num_adiciones DESC", limit=top)
    if not rows:
        return "No se encontraron contratos con adiciones excesivas."
    return f"Contratos con adiciones excesivas:\n{format_table(rows)}"


def buscar_suspensiones_repetidas(entidad: str = "", top: int = 20) -> str:
    """Busca contratos con 3 o mas suspensiones, lo que puede indicar
    problemas de ejecucion o manipulacion de plazos.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_suspensiones", where=where,
                       order="num_suspensiones DESC", limit=top)
    if not rows:
        return "No se encontraron contratos con suspensiones repetidas."
    return f"Contratos con suspensiones repetidas:\n{format_table(rows)}"


def buscar_sobrecosto(entidad: str = "", pct_minimo: float = 30, top: int = 20) -> str:
    """Busca procesos donde el valor adjudicado supera significativamente
    el precio base estimado, indicando posible sobrecosto.
    NOTA: Excluye contratos con precio_base <= 1000000 (placeholders de data entry).
    Args:
        entidad: Nombre (parcial) de la entidad.
        pct_minimo: Porcentaje minimo de sobrecosto (default: 30%).
        top: Numero maximo de resultados.
    """
    where = f"pct_sobrecosto >= {pct_minimo} AND SAFE_CAST(precio_base AS FLOAT64) > 1000000"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_sobrecosto", where=where,
                       order="pct_sobrecosto DESC", limit=top)
    if not rows:
        return "No se encontraron procesos con sobrecosto significativo (excluidos placeholders de <= $1,000,000)."
    return f"Procesos con sobrecosto vs precio base (excluidos precio_base <= $1,000,000):\n{format_table(rows)}"


def buscar_concentracion_directa(pct_minimo: float = 70, top: int = 20) -> str:
    """Busca entidades donde mas del 70% del gasto se ejecuta por contratacion
    directa, lo que puede indicar evasion de procesos competitivos.
    Args:
        pct_minimo: Porcentaje minimo de contratacion directa (default: 70%).
        top: Numero maximo de resultados.
    """
    where = f"pct_directa >= {pct_minimo}"
    rows = query_view("v_anticorr_concentracion_directa", where=where,
                       order="valor_total DESC", limit=top)
    if not rows:
        return f"No se encontraron entidades con >{pct_minimo}% contratacion directa."
    return f"Entidades con alta concentracion en contratacion directa:\n{format_table(rows)}"


def buscar_contratos_vencidos(entidad: str = "", top: int = 20) -> str:
    """Busca contratos cuya fecha de fin ya paso hace mas de 180 dias
    y que aun no han sido liquidados.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_vencidos", where=where,
                       order="dias_vencido DESC", limit=top)
    if not rows:
        return "No se encontraron contratos vencidos sin liquidar."
    return f"Contratos vencidos sin liquidar:\n{format_table(rows)}"


def buscar_sobrefacturacion(entidad: str = "", top: int = 20) -> str:
    """Busca contratos donde la suma total de facturas supera el valor
    del contrato, indicando posible sobrefacturacion.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_sobrefacturacion", where=where,
                       order="pct_sobre DESC", limit=top)
    if not rows:
        return "No se encontraron contratos con sobrefacturacion."
    return f"Contratos con sobrefacturacion:\n{format_table(rows)}"


def scoring_riesgo_entidad(entidad: str = "", top: int = 10) -> str:
    """Genera un score de riesgo (0-100) para una entidad combinando todas las
    alertas: monopolio, fraccionamiento, sin competencia, adiciones, etc.
    Args:
        entidad: Nombre (parcial) de la entidad. Si vacio, muestra el top riesgoso.
        top: Numero maximo de entidades a mostrar.
    """
    sql = f"""
    WITH scores AS (
      SELECT nombre_entidad,
        COALESCE((SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.v_anticorr_monopolista` m 
                  WHERE m.nombre_entidad = e.nombre_entidad AND m.pct_contratos_entidad > 60), 0) * 15 as s_monopolio,
        COALESCE((SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.v_anticorr_fraccionamiento` f 
                  WHERE f.nombre_entidad = e.nombre_entidad), 0) * 10 as s_fraccionamiento,
        COALESCE((SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.v_anticorr_sin_competencia` sc 
                  WHERE sc.nombre_entidad = e.nombre_entidad), 0) * 5 as s_sin_competencia,
        COALESCE((SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.v_anticorr_adiciones` a 
                  WHERE a.nombre_entidad = e.nombre_entidad), 0) * 8 as s_adiciones,
        SUM(valor_del_contrato) as valor_total
      FROM `{PROJECT}.{DATASET}.contratos_electronicos` e
      {"WHERE " + safe_like('nombre_entidad', entidad) if entidad else ""}
      GROUP BY nombre_entidad
      HAVING SUM(valor_del_contrato) > 1000000
    )
    SELECT nombre_entidad, 
           LEAST(s_monopolio + s_fraccionamiento + s_sin_competencia + s_adiciones, 100) as score_riesgo,
           s_monopolio, s_fraccionamiento, s_sin_competencia, s_adiciones, valor_total
    FROM scores
    ORDER BY score_riesgo DESC
    LIMIT {top}
    """
    rows = query(sql, max_rows=top)
    if not rows:
        return "No se pudo calcular scoring para la entidad."
    return f"Ranking de riesgo por entidad:\n{format_table(rows)}"


def diagnostico_integral(entidad: str = "", proveedor: str = "", top_por_alerta: int = 3) -> str:
    """Ejecuta un diagnostico INTEGRAL cruzando TODAS las banderas rojas de corrupcion
    simultaneamente para una entidad o proveedor.
    USA ESTA HERRAMIENTA cuando el usuario pida analisis completo de riesgo.
    Args:
        entidad: Nombre (parcial) de la entidad a diagnosticar.
        proveedor: Nombre o NIT del proveedor a diagnosticar.
        top_por_alerta: Numero de resultados por alerta (default: 3).
    """
    import json
    if not entidad and not proveedor:
        return "Debes indicar una entidad o proveedor para el diagnostico integral."
    
    target = entidad or proveedor
    result = f"DIAGNOSTICO INTEGRAL: '{target.upper()}'\n\n"
    
    alertas_activas = 0
    alertas_detalle = []
    alertas_limpias = []
    
    if entidad:
        try:
            # UNIFIED PARALLEL BIGQUERY QUERY
            sql = f"""
            WITH monopolio AS (
              SELECT 'MONOPOLIO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_monopolista` t
              WHERE pct_contratos_entidad > 50 AND {safe_like('nombre_entidad', entidad)}
            ),
            fraccionamiento AS (
              SELECT 'FRACCIONAMIENTO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_fraccionamiento` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            sin_competencia AS (
              SELECT 'SIN_COMPETENCIA' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_sin_competencia` t
              WHERE SAFE_CAST(precio_base AS FLOAT64) > 1000000 AND {safe_like('nombre_entidad', entidad)}
            ),
            adiciones AS (
              SELECT 'ADICIONES_EXCESIVAS' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_adiciones` t
              WHERE num_adiciones >= 3 AND {safe_like('nombre_entidad', entidad)}
            ),
            suspensiones AS (
              SELECT 'SUSPENSIONES' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_suspensiones` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            sobrecosto AS (
              SELECT 'SOBRECOSTO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_sobrecosto` t
              WHERE pct_sobrecosto >= 30 AND SAFE_CAST(precio_base AS FLOAT64) > 1000000 AND {safe_like('nombre_entidad', entidad)}
            ),
            vencidos AS (
              SELECT 'VENCIDOS_SIN_LIQUIDAR' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_vencidos` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            sobrefacturacion AS (
              SELECT 'SOBREFACTURACION' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_sobrefacturacion` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            concentracion AS (
              SELECT 'CONCENTRACION_DIRECTA' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_concentracion_directa` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            modificaciones AS (
              SELECT 'MODIFICACIONES_EXCESIVAS' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_modificaciones` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            sancionados AS (
              SELECT 'SANCIONADOS_CONTRATANDO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_sancionado_activo` t
              WHERE {safe_like('entidad_contratante', entidad)}
            ),
            sin_docs AS (
              SELECT 'SIN_DOCUMENTOS' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_sin_documentos` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            docs_tardios AS (
              SELECT 'DOCS_TARDIOS' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_docs_tardios` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            docs_faltantes AS (
              SELECT 'DOCS_FALTANTES' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_docs_faltantes` t
              WHERE {safe_like('nombre_entidad', entidad)}
            ),
            cdps AS (
              SELECT 'CDPS_SIN_CONTRATO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.solicitudes_cdps` t
              WHERE {safe_like('entidad', entidad)}
                AND (id_contrato IS NULL OR id_contrato = '')
                AND estado_siif NOT IN ('Cancelado', 'Con compromiso', 'Realizado')
                AND SAFE_CAST(saldo_total_a_comprometer AS FLOAT64) > 0
            ),
            baja_ej AS (
              SELECT 'BAJA_EJECUCION' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_gasto_ejecucion_entidad` t
              WHERE anio = 2025 AND pct_ejecucion < 50 AND {safe_like('nombre_entidad', entidad)}
            ),
            paa_mod AS (
              SELECT 'PAA_MODIFICACIONES_EXCESIVAS' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_paa_modificaciones` t
              WHERE num_versiones > 5 AND {safe_like('nombre_entidad', entidad)}
            ),
            tvec_monop AS (
              SELECT 'TVEC_MONOPOLIO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_monopolio` t
              WHERE pct_concentracion_valor > 70 AND valor_total_categoria > 20000000 AND {safe_like('entidad', entidad)}
            ),
            tvec_frac AS (
              SELECT 'TVEC_FRACCIONAMIENTO' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_fraccionamiento` t
              WHERE {safe_like('entidad', entidad)}
            ),
            tvec_rasp AS (
              SELECT 'TVEC_RASPADO_OLLA' AS name, COUNT(*) AS count_val, ARRAY_AGG(TO_JSON_STRING(t) LIMIT {top_por_alerta}) AS samples
              FROM `{PROJECT}.{DATASET}.v_anticorr_tvec_raspado_olla` t
              WHERE pct_gasto_diciembre > 40 AND {safe_like('entidad', entidad)}
            )
            SELECT * FROM monopolio
            UNION ALL SELECT * FROM fraccionamiento
            UNION ALL SELECT * FROM sin_competencia
            UNION ALL SELECT * FROM adiciones
            UNION ALL SELECT * FROM suspensiones
            UNION ALL SELECT * FROM sobrecosto
            UNION ALL SELECT * FROM vencidos
            UNION ALL SELECT * FROM sobrefacturacion
            UNION ALL SELECT * FROM concentracion
            UNION ALL SELECT * FROM modificaciones
            UNION ALL SELECT * FROM sancionados
            UNION ALL SELECT * FROM sin_docs
            UNION ALL SELECT * FROM docs_tardios
            UNION ALL SELECT * FROM docs_faltantes
            UNION ALL SELECT * FROM cdps
            UNION ALL SELECT * FROM baja_ej
            UNION ALL SELECT * FROM paa_mod
            UNION ALL SELECT * FROM tvec_monop
            UNION ALL SELECT * FROM tvec_frac
            UNION ALL SELECT * FROM tvec_rasp
            """
            rows = query(sql, max_rows=50)
            
            for r in rows:
                name = r['name']
                count = r['count_val'] or 0
                samples_raw = r['samples'] or []
                
                samples_raw = [s for s in samples_raw if s is not None]
                
                is_active = False
                if name == "CDPS_SIN_CONTRATO":
                    is_active = (count > 10)
                else:
                    is_active = (count > 0)
                
                if is_active:
                    alertas_activas += 1
                    detail = f"🔴 {name}: {count}+ casos\n"
                    for s_str in samples_raw[:2]:
                        try:
                            s_dict = json.loads(s_str)
                            vals = " | ".join(f"{k}={v}" for k, v in list(s_dict.items())[:4])
                            detail += f"  → {vals}\n"
                        except Exception:
                            pass
                    alertas_detalle.append(detail)
                else:
                    alertas_limpias.append(name)
                    
        except Exception:
            # FALLBACK TO THE OLD SEQUENTIAL MODE IF UNIFIED FAILS
            alertas_activas = 0
            alertas_detalle = []
            alertas_limpias = []
            
            checks = [
                ("MONOPOLIO", "v_anticorr_monopolista", 
                 f"pct_contratos_entidad > 50 AND {safe_like('nombre_entidad', entidad)}", 
                 "pct_contratos_entidad DESC"),
                ("FRACCIONAMIENTO", "v_anticorr_fraccionamiento",
                 safe_like('nombre_entidad', entidad), "valor_total_sumado DESC"),
                ("SIN_COMPETENCIA", "v_anticorr_sin_competencia",
                 f"SAFE_CAST(precio_base AS FLOAT64) > 1000000 AND {safe_like('nombre_entidad', entidad)}", "precio_base DESC"),
                ("ADICIONES_EXCESIVAS", "v_anticorr_adiciones",
                 f"num_adiciones >= 3 AND {safe_like('nombre_entidad', entidad)}", "num_adiciones DESC"),
                ("SUSPENSIONES", "v_anticorr_suspensiones",
                 safe_like('nombre_entidad', entidad), "num_suspensiones DESC"),
                ("SOBRECOSTO", "v_anticorr_sobrecosto",
                 f"pct_sobrecosto >= 30 AND SAFE_CAST(precio_base AS FLOAT64) > 1000000 AND {safe_like('nombre_entidad', entidad)}", "pct_sobrecosto DESC"),
                ("VENCIDOS_SIN_LIQUIDAR", "v_anticorr_vencidos",
                 safe_like('nombre_entidad', entidad), "dias_vencido DESC"),
                ("SOBREFACTURACION", "v_anticorr_sobrefacturacion",
                 safe_like('nombre_entidad', entidad), "pct_sobre DESC"),
                ("CONCENTRACION_DIRECTA", "v_anticorr_concentracion_directa",
                 safe_like('nombre_entidad', entidad), "pct_directa DESC"),
                ("MODIFICACIONES_EXCESIVAS", "v_anticorr_modificaciones",
                 safe_like('nombre_entidad', entidad), "num_modificaciones DESC"),
                ("SANCIONADOS_CONTRATANDO", "v_anticorr_sancionado_activo",
                 safe_like('entidad_contratante', entidad), "valor_del_contrato DESC"),
                ("SIN_DOCUMENTOS", "v_anticorr_sin_documentos",
                 safe_like('nombre_entidad', entidad), "valor_del_contrato DESC"),
                ("DOCS_TARDIOS", "v_anticorr_docs_tardios",
                 safe_like('nombre_entidad', entidad), "dias_retraso_max DESC"),
                ("DOCS_FALTANTES", "v_anticorr_docs_faltantes",
                 safe_like('nombre_entidad', entidad), "valor_del_contrato DESC"),
                ("PAA_MODIFICACIONES_EXCESIVAS", "v_anticorr_paa_modificaciones",
                 f"num_versiones > 5 AND {safe_like('nombre_entidad', entidad)}", "num_versiones DESC"),
                ("TVEC_MONOPOLIO", "v_anticorr_tvec_monopolio",
                 f"pct_concentracion_valor > 70 AND valor_total_categoria > 20000000 AND {safe_like('entidad', entidad)}", "pct_concentracion_valor DESC"),
                ("TVEC_FRACCIONAMIENTO", "v_anticorr_tvec_fraccionamiento",
                 safe_like('entidad', entidad), "num_ordenes_cercanas DESC"),
                ("TVEC_RASPADO_OLLA", "v_anticorr_tvec_raspado_olla",
                 f"pct_gasto_diciembre > 40 AND {safe_like('entidad', entidad)}", "pct_gasto_diciembre DESC"),
            ]
            
            for name, view, where, order in checks:
                try:
                    rows = query_view(view, where=where, order=order, limit=top_por_alerta)
                except Exception:
                    rows = []
                if rows:
                    alertas_activas += 1
                    detail = f"🔴 {name}: {len(rows)}+ casos\n"
                    for r in rows[:2]:
                        vals = " | ".join(f"{k}={v}" for k, v in list(r.items())[:4])
                        detail += f"  → {vals}\n"
                    alertas_detalle.append(detail)
                else:
                    alertas_limpias.append(name)
            
            try:
                sql_cdp = f"""
                SELECT COUNT(*) as cdps_sin_contrato, 
                       SUM(SAFE_CAST(saldo_total_a_comprometer AS FLOAT64)) as valor_en_riesgo
                FROM {T}.solicitudes_cdps`
                WHERE {safe_like('entidad', entidad)}
                  AND (id_contrato IS NULL OR id_contrato = '')
                  AND estado_siif NOT IN ('Cancelado', 'Con compromiso', 'Realizado')
                  AND SAFE_CAST(saldo_total_a_comprometer AS FLOAT64) > 0
                """
                rows_cdp = query(sql_cdp, max_rows=1)
                if rows_cdp and rows_cdp[0].get('cdps_sin_contrato', 0) and rows_cdp[0]['cdps_sin_contrato'] > 10:
                    alertas_activas += 1
                    n = rows_cdp[0]['cdps_sin_contrato']
                    v = rows_cdp[0].get('valor_en_riesgo', 0) or 0
                    alertas_detalle.append(f"🔴 CDPS_SIN_CONTRATO: {n} CDPs por ${v:,.0f} sin contrato asociado\n")
                else:
                    alertas_limpias.append("CDPS_SIN_CONTRATO")
            except Exception:
                alertas_limpias.append("CDPS_SIN_CONTRATO")
            
            try:
                rows_ej = query_view("v_gasto_ejecucion_entidad", 
                                     where=f"anio = 2025 AND pct_ejecucion < 50 AND {safe_like('nombre_entidad', entidad)}",
                                     order="pct_ejecucion ASC", limit=3)
                if rows_ej:
                    alertas_activas += 1
                    pct = rows_ej[0].get('pct_ejecucion', 'N/A')
                    alertas_detalle.append(f"🔴 BAJA_EJECUCION: Solo {pct}% de ejecucion presupuestal en 2025\n")
                else:
                    alertas_limpias.append("BAJA_EJECUCION")
            except Exception:
                alertas_limpias.append("BAJA_EJECUCION")
    
    if proveedor:
        where = f"(LOWER(proveedor_sancionado) LIKE '%{proveedor.lower()}%' OR nit_sancionado = '{proveedor}')"
        rows = query_view("v_anticorr_sancionado_activo", where=where,
                          order="valor_del_contrato DESC", limit=top_por_alerta)
        if rows:
            alertas_activas += 1
            alertas_detalle.append(f"🔴 SANCIONADO_ACTIVO: {len(rows)} contratos post-sancion\n")
        else:
            alertas_limpias.append("SANCIONADO")
    
    # Build result
    for d in alertas_detalle:
        result += d + "\n"
    
    if alertas_limpias:
        result += f"✅ Sin alertas en: {', '.join(alertas_limpias)}\n\n"
    
    total = alertas_activas + len(alertas_limpias)
    result += f"RESUMEN: {alertas_activas}/{total} banderas activas — "
    if alertas_activas == 0:
        result += "Riesgo BAJO"
    elif alertas_activas <= 3:
        result += "Riesgo MEDIO"
    elif alertas_activas <= 6:
        result += "Riesgo ALTO"
    else:
        result += "Riesgo CRITICO"
    
    return result


def buscar_contratos_sin_documentos(entidad: str = "", top: int = 15) -> str:
    """Busca contratos de mas de $50M que NO tienen ningun documento soporte
    en el sistema SECOP II. Indica posible contratacion sin trazabilidad documental.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_sin_documentos", where=where,
                       order="valor_del_contrato DESC", limit=top)
    if not rows:
        return "No se encontraron contratos sin documentos."
    return f"Contratos sin documentos soporte:\n{format_table(rows)}"


def buscar_documentos_tardios(entidad: str = "", top: int = 15) -> str:
    """Busca contratos donde se cargaron documentos mas de 90 dias DESPUES de
    terminado el contrato. Posible fabricacion retroactiva de soportes.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_docs_tardios", where=where,
                       order="dias_retraso_max DESC", limit=top)
    if not rows:
        return "No se encontraron documentos tardios."
    return f"Contratos con documentos cargados despues del cierre:\n{format_table(rows)}"


def buscar_docs_faltantes(entidad: str = "", top: int = 15) -> str:
    """Busca contratos de mas de $100M (no directa) que no tienen documentos
    obligatorios como estudios previos o CDP. Posible incumplimiento normativo.
    Args:
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if entidad:
        where += f" AND {safe_like('nombre_entidad', entidad)}"
    rows = query_view("v_anticorr_docs_faltantes", where=where,
                       order="valor_del_contrato DESC", limit=top)
    if not rows:
        return "No se encontraron contratos con documentos faltantes."
    return f"Contratos sin documentos obligatorios:\n{format_table(rows)}"


def listar_documentos_contrato(id_contrato: str = "", entidad: str = "", top: int = 30) -> str:
    """Lista todos los documentos (archivos) asociados a un contrato especifico
    o a los contratos de una entidad. Muestra nombre, tipo, fecha de carga.
    Args:
        id_contrato: ID del contrato (ej: CO1.PCCNTR.1234567).
        entidad: Nombre (parcial) de la entidad.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if id_contrato:
        where += f" AND n_mero_de_contrato = '{id_contrato}'"
    if entidad:
        where += f" AND {safe_like('entidad', entidad)}"
    if not id_contrato and not entidad:
        return "Debes indicar un id_contrato o entidad."
    rows = query_view("archivos_secop", where=where,
                       order="fecha_carga DESC", limit=top)
    return f"Documentos del contrato:\n{format_table(rows)}"


def detectar_colusion_representante(proveedor: str = "", entidad: str = "", top: int = 5) -> str:
    """Detecta COLUSIÓN (bid rigging) y REDES DE PROVEEDORES separadamente.
    COLUSIÓN = Empresas con el mismo representante legal que presentaron ofertas en el MISMO proceso 
    licitatorio, haciéndose pasar por competidores independientes (manipulación de licitaciones, OCDE).
    RED DE PROVEEDORES = Empresas que comparten representante legal y contratan con las mismas 
    entidades, pero NO necesariamente compiten en los mismos procesos. Esto es sospechoso pero NO es colusión.
    Si NO se proporciona un proveedor, busca de forma general.
    Args:
        proveedor: Nombre o NIT del proveedor/contratista a analizar (opcional).
        entidad: Nombre o sigla de la entidad publica para filtrar (opcional).
        top: Numero maximo de conexiones a mostrar (MAXIMO 5 para evitar errores de URL en Telegram).
    """
    if not proveedor or proveedor.strip() == "":
        # === STEP 1: Detect REAL COLLUSION (bid rigging) - same rep, same process ===
        ent_filter_prop = ""
        ent_filter_ce = ""
        if entidad:
            ent_filter_prop = f"AND {safe_like('pp1.entidad_compradora', entidad)}"
            ent_filter_ce = f"AND {safe_like('nombre_entidad', entidad)}"

        sql_colusion = f"""
        WITH rep_companies AS (
          SELECT DISTINCT 
            identificacion_representante_legal AS rep_id,
            nombre_representante_legal AS rep_name,
            documento_proveedor AS nit,
            proveedor_adjudicado AS empresa
          FROM `{PROJECT}.{DATASET}.contratos_electronicos`
          WHERE identificacion_representante_legal IS NOT NULL
            AND identificacion_representante_legal NOT IN ('0', '', 'No Definido', 'No aplica', 'Sin Descripcion')
            AND nombre_representante_legal NOT IN ('Sin Descripcion', 'No Definido', '', 'No aplica')
            AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
            {JUNK_FILTER_SQL}
            {ent_filter_ce}
        )
        SELECT DISTINCT
          r1.rep_name AS representante,
          r1.rep_id AS cc_representante,
          r1.empresa AS empresa_1,
          r1.nit AS nit_1,
          r2.empresa AS empresa_2,
          r2.nit AS nit_2,
          pp1.id_procedimiento AS proceso,
          pp1.entidad_compradora AS entidad
        FROM rep_companies r1
        JOIN rep_companies r2 ON r1.rep_id = r2.rep_id AND r1.nit < r2.nit
        JOIN `{PROJECT}.{DATASET}.proponentes_proceso` pp1 ON pp1.nit_proveedor = r1.nit
        JOIN `{PROJECT}.{DATASET}.proponentes_proceso` pp2 ON pp2.nit_proveedor = r2.nit 
          AND pp2.id_procedimiento = pp1.id_procedimiento
        WHERE 1=1 {ent_filter_prop}
        ORDER BY r1.rep_name
        LIMIT {top * 3}
        """

        # === STEP 2: Provider networks (shared rep, no same-process competition) ===
        where_clause = f"""
          identificacion_representante_legal IS NOT NULL 
          AND identificacion_representante_legal NOT IN ('0', '', 'No Definido', 'No aplica', 'Sin Descripcion')
          AND nombre_representante_legal IS NOT NULL
          AND nombre_representante_legal NOT IN ('Sin Descripcion', 'No Definido', '', 'No aplica')
          AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
          {JUNK_FILTER_SQL}
        """
        if entidad:
            where_clause += f" AND {safe_like('nombre_entidad', entidad)}"

        sql_redes = f"""
        SELECT 
          nombre_representante_legal AS representante,
          identificacion_representante_legal AS cc_representante,
          ARRAY_TO_STRING(ARRAY_AGG(DISTINCT proveedor_adjudicado LIMIT 5), '|') AS empresas_nombres,
          COUNT(DISTINCT documento_proveedor) AS empresas_representadas,
          COUNT(DISTINCT id_contrato) AS total_contratos,
          SUM(CAST(valor_del_contrato AS INT64)) AS valor_total_adjudicado
        FROM `{PROJECT}.{DATASET}.contratos_electronicos`
        WHERE {where_clause}
        GROUP BY representante, cc_representante
        HAVING COUNT(DISTINCT documento_proveedor) > 1
        ORDER BY total_contratos DESC, valor_total_adjudicado DESC
        LIMIT {top}
        """

        try:
            from agent.tools_graficos import generar_red_consorcios

            # Collusion query can be expensive without entity filter — handle timeout gracefully
            try:
                colusion_rows = query(sql_colusion, max_rows=top * 3, timeout_sec=45)
            except Exception:
                colusion_rows = []  # Timeout or error — skip collusion section

            red_rows = query(sql_redes, max_rows=top, timeout_sec=45)

            result = ""

            # --- SECTION 1: TRUE COLLUSION (bid rigging) ---
            if colusion_rows:
                nodes_c = {}
                edges_c = []
                for r in colusion_rows:
                    rep = "👤 " + (r['representante'][:15] + "..." if len(r['representante']) > 15 else r['representante'])
                    e1 = "🏢 " + (r['empresa_1'][:15] + "..." if len(r['empresa_1']) > 15 else r['empresa_1'])
                    e2 = "🏢 " + (r['empresa_2'][:15] + "..." if len(r['empresa_2']) > 15 else r['empresa_2'])
                    for n in [rep, e1, e2]:
                        if n not in nodes_c:
                            nodes_c[n] = {"val": 0, "contr": 0}
                    edges_c.append((rep, e1, 1))
                    edges_c.append((rep, e2, 1))
                    edges_c.append((e1, e2, 1))  # bidding on same process

                chart_col = generar_red_consorcios(
                    titulo=f"Colusión Detectada (Bid Rigging) - {entidad.upper() if entidad else 'General'}",
                    central_node=None, nodes=nodes_c, edges=edges_c
                )
                result += f"=== 🚨 COLUSIÓN DETECTADA (BID RIGGING / MANIPULACIÓN DE LICITACIONES) ===\n"
                result += f"Definición: Empresas con el MISMO representante legal que presentaron ofertas como supuestos competidores independientes en el MISMO proceso licitatorio. Esto constituye manipulación de la competencia según la OCDE.\n\n"
                result += f"{chart_col}\n\n"
                result += format_table(colusion_rows) + "\n\n"
            else:
                result += f"✅ COLUSIÓN (BID RIGGING): No se detectaron empresas con representante compartido que hayan competido en el mismo proceso licitatorio.\n\n"

            # --- SECTION 2: PROVIDER NETWORKS (shared rep, not necessarily collusion) ---
            if red_rows:
                # Collect ALL company names from all networks to query stats
                all_company_names = set()
                for r in red_rows:
                    empresas = [e.strip() for e in str(r.get('empresas_nombres', '')).split('|') if e.strip()]
                    all_company_names.update(empresas)
                
                # Get per-company stats by NAME (not by rep ID — consortiums may have different rep)
                company_stats = {}
                if all_company_names:
                    names_str = ", ".join(f"'{n.replace(chr(39), chr(39)+chr(39))}'" for n in list(all_company_names)[:30])
                    try:
                        sql_company_stats = f"""
                        SELECT 
                          proveedor_adjudicado AS empresa,
                          COUNT(DISTINCT id_contrato) AS contratos,
                          SUM(CAST(valor_del_contrato AS INT64)) AS valor
                        FROM `{PROJECT}.{DATASET}.contratos_electronicos`
                        WHERE proveedor_adjudicado IN ({names_str})
                          AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
                        GROUP BY empresa
                        """
                        cs_rows = query(sql_company_stats, max_rows=100, timeout_sec=30)
                        for cs in cs_rows:
                            company_stats[cs['empresa']] = {"val": cs.get('valor', 0) or 0, "contr": cs.get('contratos', 0) or 0}
                    except Exception:
                        pass  # Fall back to 0 values if stats query fails

                nodes_r = {}
                edges_r = []
                for r in red_rows:
                    rep = "👤 " + (r['representante'][:15] + "..." if len(r['representante']) > 15 else r['representante'])
                    if rep not in nodes_r:
                        nodes_r[rep] = {"val": r.get('valor_total_adjudicado', 0), "contr": r.get('total_contratos', 0)}
                    empresas = [e.strip() for e in str(r.get('empresas_nombres', '')).split('|') if e.strip()]
                    for emp in empresas:
                        emp_name = "🏢 " + (emp[:15] + "..." if len(emp) > 15 else emp)
                        if emp_name not in nodes_r:
                            stats = company_stats.get(emp, {"val": 0, "contr": 0})
                            nodes_r[emp_name] = {"val": stats["val"], "contr": stats["contr"]}
                        edges_r.append((rep, emp_name, 1))

                chart_red = generar_red_consorcios(
                    titulo=f"Red de Proveedores (Representación Compartida) - {entidad.upper() if entidad else 'General'}",
                    central_node=None, nodes=nodes_r, edges=edges_r
                )
                result += f"=== 🔍 RED DE PROVEEDORES (REPRESENTACIÓN COMPARTIDA) ===\n"
                result += f"Nota: Estas personas representan múltiples empresas proveedoras. Esto NO es colusión per se, pero indica una red empresarial que amerita seguimiento.\n\n"
                result += f"{chart_red}\n\n"
                for r in red_rows:
                    if 'empresas_nombres' in r:
                        del r['empresas_nombres']
                result += format_table(red_rows) + "\n\n"

            if not colusion_rows and not red_rows:
                return f"No se encontraron redes de representantes compartidos{' para ' + entidad.upper() if entidad else ''}."

            return result
        except Exception as e:
            return f"Error al buscar redes de colusión: {e}"


    clean_p = strip_accents(proveedor.lower()).replace("'", "''")
    
    # 1. Obtener la identificacion del representante legal del proveedor objetivo
    sql_rep = f"""
    SELECT DISTINCT identificacion_representante_legal, nombre_representante_legal, proveedor_adjudicado, documento_proveedor
    FROM `{PROJECT}.{DATASET}.contratos_electronicos`
    WHERE (LOWER(REGEXP_REPLACE(NORMALIZE(proveedor_adjudicado, NFD), r'\\pM', '')) LIKE '%{clean_p}%'
       OR documento_proveedor = '{proveedor}')
       AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
       {"AND " + safe_like('nombre_entidad', entidad) if entidad else ""}
    LIMIT 1
    """
    rep_rows = query(sql_rep, max_rows=1)
    if not rep_rows:
        return f"No se encontro informacion del representante legal para el contratista '{proveedor}'{' en ' + entidad.upper() if entidad else ''}."
        
    rep_id = rep_rows[0]['identificacion_representante_legal']
    rep_name = rep_rows[0]['nombre_representante_legal']
    target_name = rep_rows[0]['proveedor_adjudicado']
    target_nit = rep_rows[0]['documento_proveedor']
    
    if not rep_id or rep_id == '0' or rep_id == '':
        return f"El contratista '{target_name}' no posee un numero de representante legal valido registrado en contratos."
        
    # 2. Buscar otras empresas representadas por la misma persona y ver en que entidades tienen contratos
    sql_network = f"""
    WITH target_rep AS (
      SELECT '{rep_id}' AS rep_id, '{target_nit}' AS target_nit
    ),
    shared_companies AS (
      -- Otras empresas con el mismo representante legal
      SELECT DISTINCT documento_proveedor, proveedor_adjudicado
      FROM `{PROJECT}.{DATASET}.contratos_electronicos`
      WHERE identificacion_representante_legal = (SELECT rep_id FROM target_rep)
        AND documento_proveedor != (SELECT target_nit FROM target_rep)
        AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
        {"AND " + safe_like('nombre_entidad', entidad) if entidad else ""}
    ),
    shared_contracts AS (
      -- Entidades comunes
      SELECT 
        c2.proveedor_adjudicado AS empresa_socia,
        c2.documento_proveedor AS nit_socia,
        c1.nombre_entidad AS entidad,
        COUNT(DISTINCT c1.id_contrato) AS contratos_mi_empresa,
        COUNT(DISTINCT c2.id_contrato) AS contratos_empresa_socia,
        SUM(CAST(c1.valor_del_contrato AS INT64)) AS valor_mi_empresa,
        SUM(CAST(c2.valor_del_contrato AS INT64)) AS valor_empresa_socia
      FROM `{PROJECT}.{DATASET}.contratos_electronicos` c1
      JOIN `{PROJECT}.{DATASET}.contratos_electronicos` c2 ON c1.nombre_entidad = c2.nombre_entidad
      CROSS JOIN target_rep tr
      WHERE c1.documento_proveedor = tr.target_nit
        AND c2.documento_proveedor IN (SELECT documento_proveedor FROM shared_companies)
        AND c1.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
        AND c2.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
        {"AND " + safe_like('c1.nombre_entidad', entidad) if entidad else ""}
      GROUP BY empresa_socia, nit_socia, entidad
    )
    SELECT * FROM shared_contracts
    ORDER BY contratos_empresa_socia DESC, valor_empresa_socia DESC
    LIMIT {top}
    """
    
    network_rows = query(sql_network, max_rows=top)
    
    result = f"=== ANÁLISIS DE REPRESENTACIÓN COMPARTIDA (SECOP II) ===\n\n"
    result = result + f"Contratista analizado: {target_name} (NIT: {target_nit})\n"
    result = result + f"Representante Legal: {rep_name} (CC/NIT: {rep_id})\n"
    if entidad:
        result = result + f"Entidad: {entidad.upper()}\n"
    result = result + "\n"
    
    if not network_rows:
        result = result + f"✅ No se detectaron otras empresas activas que compartan el mismo representante legal en tus entidades habituales de contratacion. Riesgo de colusion bajo."
        return result
        
    try:
        sql_self = f"""
        SELECT 
          COUNT(DISTINCT id_contrato) AS num_contratos, 
          SUM(CAST(valor_del_contrato AS INT64)) AS valor_total 
        FROM `{PROJECT}.{DATASET}.contratos_electronicos`
        WHERE (proveedor_adjudicado = '{target_name}' OR documento_proveedor = '{target_nit}')
        """
        self_rows = query(sql_self, max_rows=1)
        self_contr = int(self_rows[0]['num_contratos'] or 0) if self_rows else 0
        self_val = float(self_rows[0]['valor_total'] or 0) if self_rows else 0
    except Exception:
        self_contr = 0
        self_val = 0.0

    nodes = {}
    edges = []
    
    nodes[target_name] = {"val": self_val, "contr": self_contr}
    
    for pr in network_rows:
        p_name = pr['empresa_socia']
        nodes[p_name] = {"val": float(pr.get('valor_empresa_socia', 0) or 0), "contr": int(pr.get('contratos_empresa_socia', 0) or 0)}
        edges.append((target_name, p_name, int(pr.get('contratos_empresa_socia', 0) or 0)))
        
    from agent.tools_graficos import generar_red_consorcios
    chart_token = generar_red_consorcios(
        titulo=f"Red de Representación Compartida - {target_name}",
        central_node=target_name,
        nodes=nodes,
        edges=edges
    )
    
    result = result + f"{chart_token}\n\n"

    # 2.5. Check for REAL COLLUSION (bid rigging) - same rep companies bidding on same process
    shared_nits = [pr['nit_socia'] for pr in network_rows]
    all_nits = [target_nit] + shared_nits
    nit_list = ", ".join(f"'{n}'" for n in all_nits)
    sql_bid_rigging = f"""
    SELECT DISTINCT
      pp1.nit_proveedor AS nit_1,
      pp1.proveedor AS empresa_1,
      pp2.nit_proveedor AS nit_2,
      pp2.proveedor AS empresa_2,
      pp1.id_procedimiento AS proceso,
      pp1.entidad_compradora AS entidad
    FROM `{PROJECT}.{DATASET}.proponentes_proceso` pp1
    JOIN `{PROJECT}.{DATASET}.proponentes_proceso` pp2 
      ON pp1.id_procedimiento = pp2.id_procedimiento 
      AND pp1.nit_proveedor < pp2.nit_proveedor
    WHERE pp1.nit_proveedor IN ({nit_list})
      AND pp2.nit_proveedor IN ({nit_list})
    ORDER BY pp1.id_procedimiento
    LIMIT 15
    """
    try:
        bid_rigging_rows = query(sql_bid_rigging, max_rows=15)
    except Exception:
        bid_rigging_rows = []

    if bid_rigging_rows:
        result += f"🚨🚨 COLUSIÓN DETECTADA (BID RIGGING / MANIPULACIÓN DE LICITACIONES) 🚨🚨\n"
        result += f"Las siguientes empresas del MISMO representante legal ({rep_name}) presentaron ofertas como supuestos competidores independientes en el MISMO proceso licitatorio. Según la OCDE, esto constituye manipulación de la competencia (bid rigging):\n\n"
        result += format_table(bid_rigging_rows) + "\n\n"
    else:
        result += f"✅ COLUSIÓN (BID RIGGING): No se detectaron empresas de {rep_name} que hayan competido en el mismo proceso licitatorio.\n\n"

    result += f"🔍 RED DE PROVEEDORES (REPRESENTACIÓN COMPARTIDA):\n"
    result += f"La misma persona ({rep_name}) representa a varias empresas que contratan con las mismas entidades públicas. Esto NO es colusión per se, pero indica una red empresarial que amerita seguimiento:\n\n"
    result = result + format_table(network_rows) + "\n\n"
    
    # 3. Detalle de CADA contrato del representante (para evitar alucinaciones del LLM)
    ent_filter = f"AND {safe_like('nombre_entidad', entidad)}" if entidad else ""
    sql_detail = f"""
    SELECT
      id_contrato,
      proveedor_adjudicado AS empresa,
      nombre_entidad AS entidad,
      SUBSTR(objeto_del_contrato, 1, 100) AS objeto,
      CAST(valor_del_contrato AS INT64) AS valor,
      estado_contrato AS estado,
      fecha_de_firma,
      urlproceso AS url
    FROM `{PROJECT}.{DATASET}.contratos_electronicos`
    WHERE identificacion_representante_legal = '{rep_id}'
      AND estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
      {ent_filter}
    ORDER BY valor_del_contrato DESC
    LIMIT 20
    """
    detail_rows = query(sql_detail, max_rows=20)
    if detail_rows:
        total_valor = sum(r.get('valor', 0) or 0 for r in detail_rows)
        empresas_unicas = set(r.get('empresa', '') for r in detail_rows)
        result += f"=== DETALLE DE CONTRATOS DE {rep_name} (CC: {rep_id}) ===\n"
        result += f"Total contratos: {len(detail_rows)} | Empresas: {len(empresas_unicas)} | Valor total: ${total_valor:,.0f}\n\n"
        result += format_table(detail_rows) + "\n\n"
    
    result += f"IMPORTANTE: Todos los datos, valores y URLs arriba son extraidos directamente de SECOP II. No modifiques, completes ni inventes datos que no esten en esta respuesta.\n\n"
    result += f"Nota: Compartir representante legal en los mismos nichos publicos incrementa drasticamente el riesgo de fraccionamiento, acuerdos colusivos en licitaciones o direccionamiento de convocatorias. Se recomienda auditar los proponentes en los procesos donde coincidieron estas empresas."
    return result


# Registry of all tools for ADK
TOOLS = [
    buscar_proveedor_monopolista,
    detectar_fraccionamiento,
    buscar_sin_competencia,
    buscar_proveedor_sancionado,
    buscar_adiciones_excesivas,
    buscar_suspensiones_repetidas,
    buscar_sobrecosto,
    buscar_concentracion_directa,
    buscar_contratos_vencidos,
    buscar_contratos_sin_documentos,
    buscar_documentos_tardios,
    buscar_docs_faltantes,
    buscar_sobrefacturacion,
    scoring_riesgo_entidad,
    diagnostico_integral,
    listar_documentos_contrato,
    detectar_colusion_representante,
]


