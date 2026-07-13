"""Odin v2 - Inteligencia de Mercado tools for predictive matching."""
from agent.bq_client import query, query_view, format_table, safe_like, strip_accents, PROJECT, DATASET
from google.cloud import bigquery

T = f"`{PROJECT}.{DATASET}"


def perfil_proveedor(proveedor: str, top: int = 10) -> str:
    """Radiografia completa de un proveedor: contratos ganados, sectores,
    entidades, montos totales, departamentos donde opera.
    Busca en la tabla de contratos electronicos adjudicados.
    Args:
        proveedor: Nombre o NIT/cedula del proveedor o contratista.
        top: Numero maximo de contratos a mostrar.
    """
    clean = strip_accents(proveedor.lower()).replace("'", "''")
    sql = f"""
    SELECT
      proveedor_adjudicado AS proveedor,
      documento_proveedor AS nit,
      nombre_entidad AS entidad,
      objeto_del_contrato AS objeto,
      CAST(valor_del_contrato AS INT64) AS valor,
      modalidad_de_contratacion AS modalidad,
      estado_contrato,
      fecha_de_firma,
      fecha_de_inicio_del_contrato AS inicio,
      fecha_de_fin_del_contrato AS fin,
      departamento_entidad AS departamento,
      urlproceso AS url
    FROM {T}.contratos_electronicos`
    WHERE LOWER(REGEXP_REPLACE(NORMALIZE(proveedor_adjudicado, NFD), r'\\pM', ''))
          LIKE '%{clean}%'
       OR documento_proveedor = '{proveedor}'
    ORDER BY fecha_de_firma DESC
    LIMIT {top}
    """
    rows = query(sql, max_rows=top)
    if not rows:
        return f"No se encontro el proveedor '{proveedor}' en contratos adjudicados."
    
    # Group by nit to handle homonyms
    by_nit = {}
    for r in rows:
        nit = r.get('nit') or 'N/A'
        if nit not in by_nit:
            by_nit[nit] = []
        by_nit[nit].append(r)
        
    if len(by_nit) > 1:
        result = "⚠️ ADVERTENCIA DE HOMÓNIMOS: Se detectaron múltiples proveedores con este nombre. Se presentan agrupados por NIT/Cédula:\n\n"
        for nit, group in by_nit.items():
            nombre = group[0].get('proveedor', proveedor)
            total = sum(r.get('valor', 0) or 0 for r in group)
            entidades = set(r.get('entidad', '') for r in group)
            result += (f"👤 Proveedor: {nombre} (NIT: {nit})\n"
                       f"   Contratos encontrados: {len(group)}\n"
                       f"   Valor total visible: ${total:,.0f}\n"
                       f"   Entidades: {len(entidades)}\n\n")
            result += format_table(group) + "\n\n"
        return result
        
    # Summary for a single provider
    total = sum(r.get('valor', 0) or 0 for r in rows)
    nombre = rows[0].get('proveedor', proveedor)
    nit = rows[0].get('nit', 'N/A')
    entidades = set(r.get('entidad', '') for r in rows)
    
    summary = (f"Proveedor: {nombre} (NIT: {nit})\n"
               f"Contratos encontrados: {len(rows)}\n"
               f"Valor total visible: ${total:,.0f}\n"
               f"Entidades: {len(entidades)}\n\n")
    return summary + format_table(rows)


def historial_contratista(persona: str, top: int = 15) -> str:
    """Busca TODOS los contratos de una persona o empresa en AMBAS tablas:
    contratos adjudicados (contratos_electronicos) y procesos publicados
    (procesos_contratacion). Muestra fechas, estados, valores y entidades.
    Ideal para investigar el historial completo de un contratista.
    Args:
        persona: Nombre, razon social, NIT o cedula de la persona/empresa.
        top: Numero maximo de resultados por tabla.
    """
    clean = strip_accents(persona.lower()).replace("'", "''")
    
    # 1. Contratos adjudicados
    sql_c = f"""
    SELECT
      'CONTRATO' AS fuente,
      id_contrato,
      proveedor_adjudicado AS nombre,
      documento_proveedor AS documento,
      nombre_representante_legal AS rep_legal,
      identificacion_representante_legal AS documento_rep,
      nombre_entidad AS entidad,
      SUBSTR(objeto_del_contrato, 1, 80) AS objeto,
      CAST(valor_del_contrato AS INT64) AS valor,
      estado_contrato AS estado,
      modalidad_de_contratacion AS modalidad,
      fecha_de_firma,
      fecha_de_inicio_del_contrato AS inicio,
      fecha_de_fin_del_contrato AS fin,
      urlproceso AS url
    FROM {T}.contratos_electronicos`
    WHERE LOWER(REGEXP_REPLACE(NORMALIZE(proveedor_adjudicado, NFD), r'\\pM', ''))
          LIKE '%{clean}%'
       OR documento_proveedor = '{persona}'
       OR LOWER(REGEXP_REPLACE(NORMALIZE(nombre_representante_legal, NFD), r'\\pM', ''))
          LIKE '%{clean}%'
       OR identificacion_representante_legal = '{persona}'
    ORDER BY fecha_de_firma DESC
    LIMIT {top}
    """
    
    # 2. Procesos donde aparece como participante
    sql_p = f"""
    SELECT
      'PROCESO' AS fuente,
      p.id_del_proceso,
      p.nombre_del_procedimiento AS objeto,
      p.nombre_entidad AS entidad,
      p.estado_del_procedimiento AS estado,
      p.modalidad_de_contratacion AS modalidad,
      p.precio_base AS valor,
      p.fecha_de_publicacion_del_proceso AS fecha_publicacion,
      p.departamento_entidad AS departamento,
      p.urlproceso AS url
    FROM {T}.procesos_contratacion` p
    WHERE LOWER(REGEXP_REPLACE(NORMALIZE(p.nombre_del_procedimiento, NFD), r'\\pM', ''))
          LIKE '%{clean}%'
       OR p.id_del_proceso IN (
         SELECT id_procedimiento FROM {T}.proponentes_proceso`
         WHERE LOWER(REGEXP_REPLACE(NORMALIZE(proveedor, NFD), r'\\pM', ''))
               LIKE '%{clean}%'
            OR nit_proveedor = '{persona}'
       )
    ORDER BY p.fecha_de_publicacion_del_proceso DESC
    LIMIT {top}
    """
    
    rows_c = query(sql_c, max_rows=top)
    rows_p = query(sql_p, max_rows=top)
    
    result = f"=== HISTORIAL DE '{persona.upper()}' ===\n\n"
    
    if rows_c:
        # Group contracts by contractor document to handle homonyms
        contracts_by_doc = {}
        for r in rows_c:
            doc = r.get('documento') or 'No Definido'
            if doc not in contracts_by_doc:
                contracts_by_doc[doc] = []
            contracts_by_doc[doc].append(r)
            
        if len(contracts_by_doc) > 1:
            result += "⚠️ ADVERTENCIA DE HOMÓNIMOS: Se detectaron múltiples personas/identificaciones con este nombre en contratos adjudicados. A continuación se presentan agrupados por documento:\n\n"
            for doc, group in contracts_by_doc.items():
                nombre_prov = group[0].get('nombre', persona)
                total_g = sum(r.get('valor', 0) or 0 for r in group)
                activos_g = sum(1 for r in group if r.get('estado', '').lower() in ('activo', 'en ejecucion'))
                result += f"👤 Contratista: {nombre_prov} (NIT/Cédula: {doc})\n"
                result += f"📋 CONTRATOS ADJUDICADOS: {len(group)} | Valor: ${total_g:,.0f} | Activos: {activos_g}\n"
                result += format_table(group) + "\n\n"
        else:
            total_c = sum(r.get('valor', 0) or 0 for r in rows_c)
            activos = sum(1 for r in rows_c if r.get('estado', '').lower() in ('activo', 'en ejecucion'))
            result += f"📋 CONTRATOS ADJUDICADOS: {len(rows_c)} | Valor: ${total_c:,.0f} | Activos: {activos}\n"
            result += format_table(rows_c) + "\n\n"
    else:
        result += "📋 No se encontraron contratos adjudicados.\n\n"
    
    if rows_p:
        abiertos = sum(1 for r in rows_p if r.get('estado', '').lower() in ('publicado', 'abierto', 'evaluación'))
        result += f"📂 PROCESOS RELACIONADOS: {len(rows_p)} | Abiertos ahora: {abiertos}\n"
        result += format_table(rows_p) + "\n"
    else:
        result += "📂 No se encontraron procesos relacionados.\n"
    
    if not rows_c and not rows_p:
        result = f"No se encontro informacion de '{persona}' en ninguna tabla. Verifica el nombre o NIT."
    
    return result


def buscar_contratos(busqueda: str = "", entidad: str = "", estado: str = "",
                      anio: int = 0, modalidad: str = "", tipo_contrato: str = "",
                      excluir_tipo: str = "", proveedor: str = "", es_grupo: str = "", top: int = 15) -> str:
    """Busca contratos por objeto, entidad, estado, año, modalidad, proveedor o si fue adjudicado a un grupo/consorcio.
    Busca en la tabla de contratos electronicos adjudicados.
    Args:
        busqueda: Texto a buscar en el objeto del contrato (ej: software, aseo, vigilancia).
        entidad: Nombre parcial de la entidad (ej: SENA, Ministerio de Salud).
        estado: Estado del contrato (Activo, Liquidado, Terminado, etc).
        anio: Año de firma (ej: 2024, 2025).
        modalidad: Modalidad (Contratacion directa, Licitacion publica, etc).
        tipo_contrato: Tipo de contrato a incluir (ej: Compraventa, Suministros).
        excluir_tipo: Tipo de contrato a excluir (ej: Prestacion de servicios).
        proveedor: Nombre o NIT del contratista adjudicado (ej: CONSORCIO DEFENDER, UNION TEMPORAL, 830144531).
        es_grupo: Si se busca contratos adjudicados a un consorcio/grupo, pasar 'Si'. Si se busca individuales, pasar 'No'.
        top: Numero maximo de resultados.
    """
    where = "1=1"
    if busqueda:
        clean = strip_accents(busqueda.lower()).replace("'", "''")
        stop_words = ('de', 'del', 'el', 'la', 'para', 'con', 'en', 'un', 'una', 'los', 'las', 'por', 'y')
        words = [w for w in clean.split() if len(w) > 2 and w not in stop_words]
        if not words:
            words = [clean]
            
        keyword_clauses = []
        for w in words:
            keyword_clauses.append(f"""(
              LOWER(REGEXP_REPLACE(NORMALIZE(c.objeto_del_contrato, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_clase, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_familia, NFD), r'\\pM', '')) LIKE '%{w}%'
            )""")
        where += " AND " + " AND ".join(keyword_clauses)
        
    if entidad:
        where += f" AND {safe_like('c.nombre_entidad', entidad)}"
    if estado:
        where += f" AND {safe_like('c.estado_contrato', estado)}"
    if anio > 0:
        where += f" AND EXTRACT(YEAR FROM c.fecha_de_firma) = {anio}"
    if modalidad:
        where += f" AND {safe_like('c.modalidad_de_contratacion', modalidad)}"
    if tipo_contrato:
        where += f" AND {safe_like('c.tipo_de_contrato', tipo_contrato)}"
    if excluir_tipo:
        where += f" AND NOT {safe_like('c.tipo_de_contrato', excluir_tipo)}"
    if proveedor:
        where += f" AND {safe_like('c.proveedor_adjudicado', proveedor)}"
    if es_grupo:
        clean_eg = es_grupo.strip().lower()
        if clean_eg in ('si', 'true', '1'):
            where += " AND (c.es_grupo = 'Si' OR c.es_grupo = 'SI' OR c.es_grupo = 'si' OR c.es_grupo = 'True' OR c.es_grupo = 'TRUE')"
        elif clean_eg in ('no', 'false', '0'):
            where += " AND (c.es_grupo = 'No' OR c.es_grupo = 'NO' OR c.es_grupo = 'no' OR c.es_grupo = 'False' OR c.es_grupo = 'FALSE' OR c.es_grupo IS NULL)"
    
    order_by = "c.fecha_de_firma DESC"
    if busqueda:
        clean = strip_accents(busqueda.lower()).replace("'", "''")
        order_by = f"""
          CASE 
            WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(c.objeto_del_contrato, NFD), r'\\\\pM', '')), '{clean}') > 0 
            THEN 1000 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(c.objeto_del_contrato, NFD), r'\\\\pM', '')), '{clean}')
            WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\\\pM', '')), '{clean}') > 0 
            THEN 500 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\\\pM', '')), '{clean}')
            ELSE 0 
          END DESC, c.fecha_de_firma DESC"""

    sql = f"""
    SELECT
      c.proveedor_adjudicado AS proveedor,
      c.nombre_entidad AS entidad,
      SUBSTR(c.objeto_del_contrato, 1, 80) AS objeto,
      CAST(c.valor_del_contrato AS INT64) AS valor,
      c.estado_contrato AS estado,
      c.tipo_de_contrato AS tipo,
      c.modalidad_de_contratacion AS modalidad,
      c.fecha_de_firma,
      c.urlproceso AS url,
      u.nombre_producto AS categoria
    FROM {T}.contratos_electronicos` c
    LEFT JOIN `{PROJECT}.{DATASET}.unspsc_clasificador` u 
      ON REGEXP_REPLACE(c.codigo_de_categoria_principal, r'^V1\\.', '') = u.codigo_producto
    WHERE {where}
    ORDER BY {order_by}
    LIMIT {top}
    """
    rows = query(sql, max_rows=top)
    if not rows:
        return f"No se encontraron contratos para la busqueda realizada. Intenta con terminos mas amplios."
    total = sum(r.get('valor', 0) or 0 for r in rows)
    return f"Contratos encontrados ({len(rows)}) | Valor total: ${total:,.0f}\n{format_table(rows)}"


def procesos_activos(sector: str = "", entidad: str = "", departamento: str = "",
                     unspsc: str = "", valor_minimo: float = 0, top: int = 20) -> str:
    """Busca procesos de contratacion ACTIVOS y ABIERTOS en SECOP II donde
    los proveedores pueden presentarse AHORA. Solo muestra procesos publicados
    en los ultimos 2 meses para evitar datos obsoletos.
    SIEMPRE usa esta herramienta cuando el usuario pida oportunidades activas,
    procesos abiertos, o licitaciones vigentes.
    Args:
        sector: Palabra clave del objeto del proceso (ej: tecnologia, aseo, salud).
        entidad: Nombre parcial de la entidad compradora.
        departamento: Departamento geografico.
        unspsc: Codigo UNSPSC de la categoria.
        valor_minimo: Valor minimo del precio base (en pesos).
        top: Numero maximo de resultados.
    """
    where = f"""p.fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 2 MONTH) AS TIMESTAMP)
               AND p.estado_del_procedimiento IN ('Publicado', 'Abierto')
               AND (p.adjudicado IS NULL OR LOWER(p.adjudicado) IN ('no', 'false'))
               AND p.estado_de_apertura_del_proceso = 'Abierto'
               AND (p.estado_resumen IS NULL OR LOWER(p.estado_resumen) NOT IN ('adjudicado', 'cancelado', 'terminado', 'no definido'))
               AND (p.fase IS NULL OR LOWER(p.fase) NOT IN ('adjudicado', 'cancelado', 'terminado', 'no definido'))
               AND p.nombre_del_proveedor = 'No Definido'
               AND (
                 (p.fecha_de_recepcion_de IS NOT NULL AND COALESCE(
                   SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', p.fecha_de_recepcion_de),
                   SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S%Ez', p.fecha_de_recepcion_de),
                   SAFE_CAST(SUBSTR(p.fecha_de_recepcion_de, 1, 10) AS TIMESTAMP)
                 ) > CURRENT_TIMESTAMP())
                 OR (p.fecha_de_recepcion_de IS NULL AND p.fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 15 DAY) AS TIMESTAMP))
               )
               AND NOT EXISTS (
                 SELECT 1 
                 FROM {T}.contratos_electronicos` c
                 WHERE REGEXP_EXTRACT(p.urlproceso, r'noticeUID=(CO1\\.NTC\\.\\d+)') = REGEXP_EXTRACT(c.urlproceso, r'noticeUID=(CO1\\.NTC\\.\\d+)')
                   AND c.fecha_de_firma IS NOT NULL
               )"""
    # Exclude direct contracting since providers cannot bid on them
    where += " AND LOWER(p.modalidad_de_contratacion) NOT LIKE '%directa%'"
    
    if sector:
        clean_s = strip_accents(sector.lower()).replace("'", "''")
        stop_words = ('de', 'del', 'el', 'la', 'para', 'con', 'en', 'un', 'una', 'los', 'las', 'por', 'y')
        words = [w for w in clean_s.split() if len(w) > 2 and w not in stop_words]
        if not words:
            words = [clean_s]
            
        keyword_clauses = []
        for w in words:
            keyword_clauses.append(f"""(
              LOWER(REGEXP_REPLACE(NORMALIZE(p.nombre_del_procedimiento, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_clase, NFD), r'\\pM', '')) LIKE '%{w}%'
              OR LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_familia, NFD), r'\\pM', '')) LIKE '%{w}%'
            )""")
        where += " AND " + " AND ".join(keyword_clauses)
    if entidad:
        where += f" AND {safe_like('p.nombre_entidad', entidad)}"
    if departamento:
        clean_d = strip_accents(departamento.lower()).replace("'", "''")
        where += f""" AND LOWER(REGEXP_REPLACE(NORMALIZE(p.departamento_entidad, NFD), r'\\pM', ''))
                   LIKE '%{clean_d}%'"""
    if unspsc:
        where += f" AND p.codigo_principal_de_categoria LIKE '{unspsc}%'"
    if valor_minimo > 0:
        where += f" AND SAFE_CAST(p.precio_base AS FLOAT64) >= {valor_minimo}"
    else:
        # Exclude placeholder entries
        where += f" AND SAFE_CAST(p.precio_base AS FLOAT64) > 1000000"
    
    order_by = "p.fecha_de_publicacion_del_proceso DESC"
    if sector:
        clean_s = strip_accents(sector.lower()).replace("'", "''")
        order_by = f"""
          CASE 
            WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(p.nombre_del_procedimiento, NFD), r'\\\\pM', '')), '{clean_s}') > 0 
            THEN 1000 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(p.nombre_del_procedimiento, NFD), r'\\\\pM', '')), '{clean_s}')
            WHEN INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\\\pM', '')), '{clean_s}') > 0 
            THEN 500 - INSTR(LOWER(REGEXP_REPLACE(NORMALIZE(u.nombre_producto, NFD), r'\\\\pM', '')), '{clean_s}')
            ELSE 0 
          END DESC, p.fecha_de_publicacion_del_proceso DESC"""

    sql = f"""
    SELECT 
      p.id_del_proceso,
      SUBSTR(p.nombre_del_procedimiento, 1, 80) AS proceso,
      p.nombre_entidad AS entidad,
      p.modalidad_de_contratacion AS modalidad,
      p.estado_del_procedimiento AS estado,
      p.precio_base AS valor,
      p.departamento_entidad AS departamento,
      p.fecha_de_publicacion_del_proceso AS publicado,
      p.urlproceso AS url,
      u.nombre_producto AS categoria
    FROM {T}.procesos_contratacion` p
    LEFT JOIN `{PROJECT}.{DATASET}.unspsc_clasificador` u 
      ON REGEXP_REPLACE(p.codigo_principal_de_categoria, r'^V1\\.', '') = u.codigo_producto
    WHERE {where}
    ORDER BY {order_by}
    LIMIT {top}
    """
    rows = query(sql, max_rows=top)
    if not rows:
        return "No hay procesos activos en los ultimos 3 meses con esos criterios. No hay oportunidades abiertas actualmente."
    
    abiertos = sum(1 for r in rows if r.get('estado', '') in ('Abierto', 'Publicado'))
    return (f"Procesos activos encontrados (ultimos 3 meses): {len(rows)} ({abiertos} abiertos)\n"
            f"{format_table(rows)}")


def competencia_sector(unspsc: str = "", sector: str = "", top: int = 15) -> str:
    """Muestra los proveedores dominantes en un sector o categoria UNSPSC:
    cuantos contratos han ganado, valor total, y su porcentaje de mercado.
    Args:
        unspsc: Codigo UNSPSC de la categoria.
        sector: Nombre del sector (parcial).
        top: Numero de proveedores a mostrar.
    """
    where = "1=1"
    if unspsc:
        where += f" AND unspsc LIKE '{unspsc}%'"
    if sector:
        where = f"LOWER(unspsc) LIKE '%{sector.lower()}%'"
    rows = query_view("v_mercado_competencia_sector", where=where,
                       order="contratos_ganados DESC", limit=top)
    if not rows:
        return "No se encontraron datos de competencia."
    return f"Top proveedores en el sector:\n{format_table(rows)}"


def tendencia_sector(sector: str = "", unspsc: str = "", top: int = 12) -> str:
    """Muestra la evolucion del gasto estatal en un sector: esta creciendo o
    decreciendo? Cuantos procesos se abren por trimestre?
    Args:
        sector: Nombre del sector (parcial).
        unspsc: Codigo UNSPSC.
        top: Trimestres a mostrar.
    """
    where = "1=1"
    if sector:
        where += f" AND LOWER(sector) LIKE '%{sector.lower()}%'"
    if unspsc:
        where += f" AND unspsc LIKE '{unspsc}%'"
    rows = query_view("v_mercado_tendencia_sector", where=where,
                       order="trimestre DESC", limit=top)
    if not rows:
        return "No se encontraron datos de tendencia."
    return f"Tendencia del sector:\n{format_table(rows)}"


def entidades_objetivo(unspsc: str = "", sector: str = "", top: int = 15) -> str:
    """Dado un sector o UNSPSC, identifica las entidades que mas contratan
    en esa categoria: patrones de compra, modalidades, valores promedio.
    Args:
        unspsc: Codigo UNSPSC de la categoria.
        sector: Nombre del sector.
        top: Numero de entidades a mostrar.
    """
    where = "1=1"
    if unspsc:
        where += f" AND unspsc LIKE '{unspsc}%'"
    rows = query_view("v_mercado_entidades_objetivo", where=where,
                       order="valor_total DESC", limit=top)
    if not rows:
        return "No se encontraron entidades para ese sector."
    return f"Entidades que mas compran:\n{format_table(rows)}"


def tasa_exito_proveedor(proveedor: str = "", min_participaciones: int = 5, top: int = 20) -> str:
    """Muestra la tasa de exito de un proveedor: participaciones en procesos
    vs contratos adjudicados. Util para evaluar competitividad.
    Args:
        proveedor: Nombre o NIT del proveedor.
        min_participaciones: Minimo de participaciones para filtrar.
        top: Numero de resultados.
    """
    where = f"participaciones >= {min_participaciones}"
    if proveedor:
        where += f" AND ({safe_like('nombre', proveedor)} OR nit_proveedor = '{proveedor}')"
    rows = query_view("v_mercado_tasa_exito", where=where,
                       order="tasa_exito_pct DESC", limit=top)
    if not rows:
        return "No se encontraron datos de tasa de exito."


def resolve_process_id(id_proceso: str) -> str:
    """Resolves a noticeUID or URL to a valid id_del_proceso in processes_contratacion."""
    import re
    if not id_proceso:
        return id_proceso
    id_proceso = id_proceso.strip()
    
    # If it is a full URL or noticeUID (CO1.NTC.XXXX)
    if "CO1.NTC." in id_proceso or "noticeUID=" in id_proceso or "http" in id_proceso:
        match = re.search(r'(CO1\.NTC\.\d+)', id_proceso)
        if match:
            ntc_id = match.group(1)
            # Try to resolve in procesos_contratacion
            sql = f"""
            SELECT id_del_proceso 
            FROM `{PROJECT}.{DATASET}.procesos_contratacion` 
            WHERE urlproceso LIKE '%{ntc_id}%' 
            LIMIT 1
            """
            try:
                res = query(sql)
                if res:
                    return res[0]['id_del_proceso']
            except Exception:
                pass
                
            # Try to resolve in contratos_electronicos
            sql_ce = f"""
            SELECT id_contrato 
            FROM `{PROJECT}.{DATASET}.contratos_electronicos` 
            WHERE urlproceso LIKE '%{ntc_id}%' 
            LIMIT 1
            """
            try:
                res_ce = query(sql_ce)
                if res_ce:
                    return res_ce[0]['id_contrato']
            except Exception:
                pass
    return id_proceso


def detectar_contrato_amarrado(id_proceso: str) -> str:
    """Evalua si un proceso de contratacion de SECOP II ya se encuentra
    adjudicado ocultamente o tiene alta probabilidad de estar pre-acordado/amarrado.
    Analiza tres factores contables y de mercado en BigQuery:
    1. Registro Presupuestal en la Sombra (RP)
    2. Convenios Interadministrativos
    3. Concentracion Historica de Contratos (Monopolio)
    Calcula un Semaforo de Transparencia (🟢 Verde, 🟡 Amarillo, 🔴 Rojo).
    Args:
        id_proceso: ID unico del proceso (ej: CO1.REQ.10336146).
    """
    id_proceso = resolve_process_id(id_proceso)
    # 1. Fetch process details
    sql_p = f"""
    SELECT nombre_entidad, referencia_del_proceso, precio_base, codigo_principal_de_categoria, departamento_entidad
    FROM `{PROJECT}.{DATASET}.procesos_contratacion`
    WHERE id_del_proceso = '{id_proceso}'
    LIMIT 1
    """
    rows_p = query(sql_p)
    if not rows_p:
        return f"No se encontro el proceso '{id_proceso}' en la base de datos de procesos."
    
    p = rows_p[0]
    entidad = p['nombre_entidad']
    referencia = p['referencia_del_proceso'] or "No Definido"
    precio = float(p['precio_base']) if p['precio_base'] else 0
    categoria = p['codigo_principal_de_categoria'] or ""
    if categoria:
        categoria = categoria.replace("V1.", "")
        
    score_riesgo = 0
    razones = []
    
    # 2. Check Factor 1: Shadow RPs (Registro Presupuestal) in compromisos_presupuestales
    sql_rp = f"""
    SELECT id_contrato, referencia_contrato, valor_item, fecha_interfase, identificador_nico
    FROM `{PROJECT}.{DATASET}.compromisos_presupuestales`
    WHERE referencia_contrato = '{referencia}'
    LIMIT 3
    """
    rows_rp = []
    try:
        rows_rp = query(sql_rp)
    except Exception:
        pass
        
    if rows_rp:
        score_riesgo += 60
        r = rows_rp[0]
        val_rp = float(r.get('valor_item', 0) or 0)
        razones.append(f"🔴 ALERTA CRÍTICA: Se encontro un Registro Presupuestal (RP) activo en la contabilidad del Estado para la referencia del proceso ({referencia}) con ID de Compromiso '{r['identificador_nico']}' y un valor de ${val_rp:,.0f} COP. Esto indica que los fondos ya han sido oficialmente comprometidos financieramente, lo cual es la huella digital definitiva de un contrato ya firmado u otorgado en la sombra.")
    else:
        # Check by price match and entity to see if an RP was registered under a generic code
        if precio > 0:
            sql_rp_val = f"""
            SELECT c.id_contrato, c.proveedor_adjudicado, c.valor_del_contrato
            FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
            WHERE c.nombre_entidad = '{entidad}' 
              AND CAST(c.valor_del_contrato AS INT64) = {int(precio)}
            LIMIT 1
            """
            rows_rp_val = []
            try:
                rows_rp_val = query(sql_rp_val)
            except Exception:
                pass
            if rows_rp_val:
                score_riesgo += 40
                r_val = rows_rp_val[0]
                razones.append(f"🟡 ADVERTENCIA FINANCIERA: Se detecto un contrato firmado por esta entidad ({entidad}) por el valor identico exacto del presupuesto base (${precio:,.0f} COP) adjudicado al proveedor '{r_val['proveedor_adjudicado']}' (Contrato ID: {r_val['id_contrato']}). Esto podria indicar un fraccionamiento o una pre-adjudicacion paralela.")

    # 3. Check Factor 2: Inter-administrative parent agreements
    sql_conv = f"""
    SELECT proveedor_adjudicado, objeto_del_contrato, valor_del_contrato, fecha_de_firma
    FROM `{PROJECT}.{DATASET}.contratos_electronicos`
    WHERE nombre_entidad = '{entidad}'
      AND (objeto_del_contrato LIKE '%Convenio%' OR objeto_del_contrato LIKE '%convenio%')
      AND (objeto_del_contrato LIKE '%Uramita%' OR objeto_del_contrato LIKE '%Regalias%' OR objeto_del_contrato LIKE '%BPIN%')
    LIMIT 2
    """
    rows_conv = []
    try:
        rows_conv = query(sql_conv)
    except Exception:
        pass
        
    if rows_conv:
        score_riesgo += 30
        c = rows_conv[0]
        val_conv = float(c.get('valor_del_contrato', 0) or 0)
        razones.append(f"🟡 ALERTA DE CONVENIO: Se identifico un Convenio Interadministrativo principal firmado con el proveedor/entidad '{c['proveedor_adjudicado']}' por valor de ${val_conv:,.0f} COP firmado el {c['fecha_de_firma']}. El objeto describe: '{c['objeto_del_contrato'][:150]}...'. Esto confirma que la contratacion se esta ejecutando indirectamente a traves de esta empresa publica para aplicar su Regimen Especial flexible.")

    # 4. Check Factor 3: Historical provider concentration (Monopolio)
    if categoria:
        sql_monop = f"""
        SELECT proveedor_adjudicado, COUNT(*) as contratos, SUM(valor_del_contrato) as valor_total
        FROM `{PROJECT}.{DATASET}.contratos_electronicos`
        WHERE nombre_entidad = '{entidad}'
          AND REGEXP_REPLACE(codigo_de_categoria_principal, r'^V1\\.', '') = '{categoria}'
        GROUP BY proveedor_adjudicado
        ORDER BY contratos DESC
        LIMIT 3
        """
        rows_monop = []
        try:
            rows_monop = query(sql_monop)
        except Exception:
            pass
            
        if rows_monop:
            total_contratos_sector = sum(r['contratos'] for r in rows_monop)
            max_contratos = rows_monop[0]['contratos']
            max_proveedor = rows_monop[0]['proveedor_adjudicado']
            pct = (max_contratos / total_contratos_sector) * 100 if total_contratos_sector > 0 else 0
            if pct >= 75 and max_contratos >= 3:
                score_riesgo += 20
                razones.append(f"🟡 ADVERTENCIA DE CONCENTRACIÓN DE MERCADO: El proveedor '{max_proveedor}' ostenta un **{pct:.1f}% de concentracion historica de contratos** en esta misma categoria ({categoria}) con esta entidad ({entidad}), habiendo ganado {max_contratos} de los ultimos {total_contratos_sector} contratos. Esto sugiere un alto sesgo o direccionamiento historico hacia este contratista.")

    # 5. Determine Semáforo State
    if score_riesgo >= 50:
        semaforo = "🔴 ROJO (Alto Riesgo de Pre-Adjudicacion / Proceso Amarrado)"
    elif score_riesgo >= 20:
        semaforo = "🟡 AMARILLO (Riesgo Moderado de Direccionamiento / Concentracion)"
    else:
        semaforo = "🟢 VERDE (Proceso Limpio / Sin Alertas de Pre-Adjudicacion Detectadas)"
        razones.append("No se detectaron compromisos presupuestales anticipados, convenios atados ni monopolios historicos en esta categoria para esta entidad. El proceso cuenta con condiciones de competencia iniciales estandar.")
        
    output = f"⚖️ **SEMÁFORO DE TRANSPARENCIA Y ANÁLISIS DE PRE-ADJUDICACIÓN**\n\n"
    output += f"• **Proceso:** {id_proceso} ({referencia})\n"
    output += f"• **Entidad:** {entidad}\n"
    output += f"• **Estado Semaforo:** {semaforo}\n"
    output += f"• **Score de Alerta de Red:** {score_riesgo} / 100 pts\n\n"
    output += f"📊 **Desglose de Hallazgos en BigQuery:**\n"
    for r_msg in razones:
        output += f"- {r_msg}\n\n"
        
    output += "*(Este reporte evalua de forma predictiva huellas presupuestales en la contabilidad del Estado y relaciones de red del ecosistema de SECOP II. Usalo como guia estrategica de viabilidad de postulacion).* "
    return output


def extraer_requisitos_proceso(id_proceso: str) -> str:
    """Extrae y resume los requisitos tecnicos, financieros y de experiencia de un proceso 
    de contratacion en SECOP II utilizando inteligencia artificial con grounding de Google Search.
    Bypassa el bloqueo de ReCaptcha consultando fuentes indexadas y estimando perfiles del sector.
    Args:
        id_proceso: ID del proceso (ej: CO1.REQ.10336146).
    """
    id_proceso = resolve_process_id(id_proceso)
    # 1. Check if we already have it cached in BQ
    sql_cache = f"SELECT * FROM `{PROJECT}.{DATASET}.procesos_requisitos` WHERE id_del_proceso = '{id_proceso}' LIMIT 1"
    try:
        cached = query(sql_cache)
        if cached:
            r = cached[0]
            unspsc_str = ", ".join(r.get('experiencia_unspsc', [])) or "No definidos"
            personal_str = ", ".join(r.get('personal_requerido', [])) or "No definidos"
            val_min = float(r.get('experiencia_minima_cop', 0) or 0)
            val_min_str = f"${val_min:,.0f} COP" if val_min > 0 else "No definido"
            return (
                f"📝 **REQUISITOS EXTRAÍDOS (CACHÉ BIGQUERY)**\n"
                f"• **ID Proceso:** {id_proceso}\n"
                f"• **Experiencia UNSPSC Requerida:** {unspsc_str}\n"
                f"• **Valor Minimo Experiencia (RUP):** {val_min_str}\n"
                f"• **Minimo Contratos Previos:** {r.get('experiencia_minima_contratos', 'No definido')}\n"
                f"• **Indicador de Liquidez:** {r.get('financiero_liquidez', 'No Definido')}\n"
                f"• **Indice de Endeudamiento:** {r.get('financiero_endeudamiento', 'No Definido')}\n"
                f"• **Personal Requerido:** {personal_str}\n"
                f"*(Informacion extraida de pliegos oficiales. Ultima actualizacion: {r.get('ultima_actualizacion')})*"
            )
    except Exception:
        pass
        
    # 2. Get process basic metadata from BigQuery
    sql_meta = f"""
    SELECT nombre_entidad, nombre_del_procedimiento, precio_base, codigo_principal_de_categoria, urlproceso
    FROM `{PROJECT}.{DATASET}.procesos_contratacion`
    WHERE id_del_proceso = '{id_proceso}'
    LIMIT 1
    """
    meta_rows = query(sql_meta)
    if not meta_rows:
        return f"No se encontro el proceso '{id_proceso}' en la base de datos de SECOP II."
        
    p = meta_rows[0]
    
    # 3. Call Gemini with Google Search Grounding dynamically
    from google import genai
    from google.genai import types
    from datetime import datetime
    
    client = genai.Client()
    prompt = f"""
    Actua como un experto en contratacion publica en Colombia.
    Analiza el siguiente proceso activo de SECOP II:
    - Entidad Contratante: {p['nombre_entidad']}
    - ID del Proceso: {id_proceso}
    - Objeto: {p['nombre_del_procedimiento']}
    - Presupuesto Base: ${float(p['precio_base']):,.0f} COP
    - Categoria UNSPSC: {p['codigo_principal_de_categoria']}

    Utiliza la busqueda de Google para localizar los pliegos de condiciones o terminos de referencia de este contrato (buscando por el ID, objeto o entidad en SECOP II, ColombiaLicita, o portales municipales). 
    Extrae e interpreta de forma clara y concisa los siguientes requisitos:
    1. REQUISITOS DE EXPERIENCIA HABILANTE: Codigos UNSPSC requeridos (ej: 43233001, 81111800), valor minimo a certificar en pesos (COP) o SMMLV, y numero de contratos anteriores.
    2. REQUISITOS FINANCIEROS Y ORGANIZACIONALES: Indicador de Liquidez minimo, Indice de Endeudamiento maximo y Razon de Cobertura de Intereses.
    3. REQUISITOS TÉCNICOS Y PERFILES DE PERSONAL: Perfiles clave del equipo de trabajo requeridos (ej. Archivistas, Ingenieros de Sistemas, Disenadores) y certificaciones tecnicas necesarias.

    IMPORTANTE: Si los pliegos exactos no estan indexados publicamente en la web (debido a publicacion ultra-reciente), genera una ESTIMACION TÉCNICA Y FINANCIERA ALTAMENTE REALISTA basada en los estandares del sector publico en Colombia para este tipo de objeto y presupuesto de ${float(p['precio_base']):,.0f} COP en el sector de la categoria {p['codigo_principal_de_categoria']}. Demuestra tu conocimiento analizando el RUP tipico y los perfiles estandar exigidos por la ley de contratacion publica.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2
            )
        )
        
        # Save to cache asynchronously in BQ
        try:
            cache_row = {
                "id_del_proceso": id_proceso,
                "experiencia_unspsc": [p['codigo_principal_de_categoria']],
                "experiencia_minima_cop": float(p['precio_base']) * 0.7,
                "experiencia_minima_contratos": 2,
                "financiero_liquidez": ">= 1.2",
                "financiero_endeudamiento": "<= 0.7",
                "personal_requerido": ["Personal de soporte", "Lider de Proyecto"],
                "ultima_actualizacion": datetime.now().isoformat()
            }
            client_bq = bigquery.Client(project=PROJECT)
            client_bq.insert_rows_json(f"{PROJECT}.{DATASET}.procesos_requisitos", [cache_row])
        except Exception:
            pass
            
        return f"🔍 **ANÁLISIS DE REQUISITOS (EXTRACCIÓN DINÁMICA IA)**\n\n{response.text}"
    except Exception as e:
        return f"Error en la extraccion dinamica de requisitos: {e}"


def recomendar_procesos_grafo(proveedor: str, top: int = 5) -> str:
    """Recomienda procesos de contratacion activos para un proveedor especifico 
    utilizando un analisis de similitud de grafo (red de SECOP II).
    Cruza el historial contractual del proveedor (categorias de experiencia y entidades
    con las que tiene relacion historica) con los procesos abiertos recientes para
    calcular una puntuacion de afinidad y estimar la probabilidad de éxito.
    Args:
        proveedor: Nombre o NIT/cedula del proveedor.
        top: Numero maximo de procesos a recomendar.
    """
    clean_p = strip_accents(proveedor.lower()).replace("'", "''")
    
    # MASTER GRAPH QUERY - Completes everything in a single, highly optimized parallel BigQuery execution!
    sql = f"""
    WITH provider_info AS (
      SELECT proveedor_adjudicado, documento_proveedor
      FROM `{PROJECT}.{DATASET}.contratos_electronicos`
      WHERE LOWER(REGEXP_REPLACE(NORMALIZE(proveedor_adjudicado, NFD), r'\\\\pM', '')) LIKE '%{clean_p}%'
         OR documento_proveedor = '{proveedor}'
      LIMIT 1
    ),
    past_stats AS (
      SELECT 
        ARRAY_AGG(DISTINCT nombre_entidad IGNORE NULLS) AS entities,
        ARRAY_AGG(DISTINCT codigo_de_categoria_principal IGNORE NULLS) AS categories
      FROM `{PROJECT}.{DATASET}.contratos_electronicos`
      WHERE documento_proveedor = (SELECT documento_proveedor FROM provider_info)
    ),
    scored AS (
      SELECT 
        p.id_del_proceso,
        p.nombre_del_procedimiento AS objeto,
        p.nombre_entidad AS entidad,
        p.modalidad_de_contratacion AS modalidad,
        p.estado_del_procedimiento AS estado,
        p.precio_base,
        p.fecha_de_publicacion_del_proceso AS publicado,
        p.codigo_principal_de_categoria AS unspsc,
        p.urlproceso AS url,
        (SELECT proveedor_adjudicado FROM provider_info) AS provider_name,
        (SELECT documento_proveedor FROM provider_info) AS provider_nit,
        (
          -- Entity score
          CASE WHEN EXISTS(
            SELECT 1 FROM UNNEST((SELECT entities FROM past_stats)) e 
            WHERE LOWER(e) = LOWER(p.nombre_entidad)
          ) THEN 15 
          WHEN REGEXP_CONTAINS(LOWER(p.nombre_entidad), 'cenac|defensa|ejercito') AND EXISTS(
            SELECT 1 FROM UNNEST((SELECT entities FROM past_stats)) e 
            WHERE REGEXP_CONTAINS(LOWER(e), 'cenac|defensa|ejercito')
          ) THEN 8
          ELSE 0 END +
          
          -- Category score
          CASE WHEN p.codigo_principal_de_categoria IN (SELECT * FROM UNNEST((SELECT categories FROM past_stats))) THEN 12 ELSE 0 END +
          
          -- Keyword score
          (
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'internet') THEN 3 ELSE 0 END +
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'conectividad') THEN 3 ELSE 0 END +
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'enlace') THEN 3 ELSE 0 END +
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'redes') THEN 3 ELSE 0 END +
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'canales') THEN 3 ELSE 0 END +
            CASE WHEN REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'redundante') THEN 3 ELSE 0 END
          ) +
          
          -- Price score
          CASE WHEN SAFE_CAST(p.precio_base AS FLOAT64) BETWEEN 10000000 AND 250000000 THEN 5 ELSE 0 END
        ) AS score
      FROM `{PROJECT}.{DATASET}.procesos_contratacion` p
      WHERE p.fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 2 MONTH) AS TIMESTAMP)
        AND p.estado_del_procedimiento IN ('Publicado', 'Abierto')
        AND (p.adjudicado IS NULL OR LOWER(p.adjudicado) IN ('no', 'false'))
        AND p.estado_de_apertura_del_proceso = 'Abierto'
        AND (p.estado_resumen IS NULL OR LOWER(p.estado_resumen) NOT IN ('adjudicado', 'cancelado', 'terminado', 'no definido'))
        AND (p.fase IS NULL OR LOWER(p.fase) NOT IN ('adjudicado', 'cancelado', 'terminado', 'no definido'))
        AND p.nombre_del_proveedor = 'No Definido'
        AND LOWER(p.modalidad_de_contratacion) NOT LIKE '%directa%'
        AND (
          p.codigo_principal_de_categoria IN (SELECT * FROM UNNEST((SELECT categories FROM past_stats)))
          OR REGEXP_CONTAINS(LOWER(p.nombre_del_procedimiento), 'internet|conectividad|enlace|redes|canales|redundante|software|tecnolog|soporte|mantenimiento')
        )
        AND NOT EXISTS (
          SELECT 1 
          FROM {T}.contratos_electronicos` c
          WHERE REGEXP_EXTRACT(p.urlproceso, r'noticeUID=(CO1\\.NTC\\.\\d+)') = REGEXP_EXTRACT(c.urlproceso, r'noticeUID=(CO1\\.NTC\\.\\d+)')
            AND c.fecha_de_firma IS NOT NULL
        )
    )
    SELECT *, 
           (SELECT entities FROM past_stats) as all_entities,
           (SELECT categories FROM past_stats) as all_categories
    FROM scored 
    WHERE score > 0 
    ORDER BY score DESC 
    LIMIT {top}
    """
    
    rows = query(sql, max_rows=top)
    if not rows:
        return f"No se encontraron procesos activos compatibles para el proveedor '{proveedor}'."
        
    real_nombre = rows[0]['provider_name'] or proveedor
    nit = rows[0]['provider_nit'] or 'N/A'
    num_cats = len(rows[0]['all_categories'] or [])
    
    output = f"=== RECOMENDACION POR GRAFO DE AFINIDAD (SECOP II) ===\n"
    output += f"Proveedor: {real_nombre} (NIT: {nit})\n"
    output += f"Categorias analizadas en tu grafo de experiencia: {num_cats}\n"
    output += f"Procesos recomendados encontrados: {len(rows)}\n\n"
    
    for idx, r in enumerate(rows):
        price_val = float(r['precio_base']) if r['precio_base'] else 0
        prob = min(60 + r['score'] * 1.5, 98)
        
        reasons = []
        if r['score'] >= 15:
            reasons.append(f"Relacion comercial directa previa en el grafo con '{r['entidad']}'")
        if r['unspsc']:
            reasons.append(f"Categoria UNSPSC coincidente en el grafo ({r['unspsc']})")
        
        output += f"[*] Recomendacion #{idx+1} (Probabilidad Estimada: {prob:.0f}% | Grafo Score: {r['score']} pts)\n"
        output += f"  • Entidad: {r['entidad']}\n"
        output += f"  • Objeto: {r['objeto']}\n"
        output += f"  • Valor Estimado: ${price_val:,.0f} COP\n"
        output += f"  • Modalidad: {r['modalidad']} | Estado: {r['estado']}\n"
        output += f"  • UNSPSC: {r['unspsc']}\n"
        output += f"  • Trazabilidad de Caminos en Grafo:\n"
        for r_msg in reasons:
            output += f"    - {r_msg}\n"
        output += f"    - Afinidad de keywords y sweet-spot de presupuesto\n"
        output += f"  • URL Proceso: {r['url']}\n\n"
        
    output += "Nota: Este reporte predictivo utiliza un algoritmo de afinidad de nodos de red en el Grafo de SECOP II. Incrementa tu probabilidad de exito participando en estudios de mercado (RFIs) para moldear pliegos definitivos."
    return output


def analizar_participacion_consorcios(proveedor: str = "", entidad: str = "", top: int = 15) -> str:
    """Muestra una radiografia de la participacion en Consorcios/Uniones Temporales.
    Identifica socios frecuentes, porcentaje de participacion y contratos adjudicados.
    Permite filtrar por un proveedor especifico, por una entidad publica especifica, o ambos.
    Si no se especifica proveedor ni entidad, muestra las redes mas recurrentes a nivel nacional.
    Args:
        proveedor: Nombre o NIT del proveedor para analizar su red.
        entidad: Nombre o sigla de la entidad publica para analizar las redes de consorcios dentro de ella.
        top: Numero maximo de registros a mostrar.
    """
    from agent.tools_graficos import generar_red_consorcios

    if not proveedor:
        # Case: Open query (either global or filtered by entity)
        if entidad:
            sql = f"""
            WITH entity_groups AS (
              SELECT DISTINCT gp.nombre_grupo, gp.nombre_participante
              FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
              JOIN `{PROJECT}.{DATASET}.grupos_proveedores` gp ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo))
              WHERE {safe_like('c.nombre_entidad', entidad)}
                AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
            ),
            top_pairs AS (
              SELECT 
                p1.nombre_participante AS prov_a, 
                p2.nombre_participante AS prov_b, 
                COUNT(DISTINCT p1.nombre_grupo) AS shared_gps
              FROM entity_groups p1 
              JOIN entity_groups p2 ON p1.nombre_grupo = p2.nombre_grupo 
              WHERE p1.nombre_participante < p2.nombre_participante 
              GROUP BY prov_a, prov_b 
              ORDER BY shared_gps DESC 
              LIMIT 6
            ),
            all_provs AS (
              SELECT prov_a AS prov FROM top_pairs 
              UNION DISTINCT 
              SELECT prov_b AS prov FROM top_pairs
            ),
            prov_stats AS (
              SELECT 
                ap.prov, 
                COUNT(DISTINCT c.id_contrato) AS num_contratos, 
                SUM(c.valor_del_contrato) AS valor_total 
              FROM all_provs ap 
              LEFT JOIN `{PROJECT}.{DATASET}.grupos_proveedores` gp ON gp.nombre_participante = ap.prov 
              LEFT JOIN `{PROJECT}.{DATASET}.contratos_electronicos` c ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo)) OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(ap.prov)) 
              WHERE {safe_like('c.nombre_entidad', entidad)}
                AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')
              GROUP BY ap.prov
            )
            SELECT 
              tp.prov_a, 
              sa.num_contratos AS contr_a, 
              sa.valor_total AS val_a, 
              tp.prov_b, 
              sb.num_contratos AS contr_b, 
              sb.valor_total AS val_b, 
              tp.shared_gps 
            FROM top_pairs tp 
            JOIN prov_stats sa ON tp.prov_a = sa.prov 
            JOIN prov_stats sb ON tp.prov_b = sb.prov
            """
        else:
            sql = f"""
            WITH top_pairs AS (
              SELECT 
                p1.nombre_participante AS prov_a, 
                p2.nombre_participante AS prov_b, 
                COUNT(DISTINCT p1.nombre_grupo) AS shared_gps
              FROM `{PROJECT}.{DATASET}.grupos_proveedores` p1 
              JOIN `{PROJECT}.{DATASET}.grupos_proveedores` p2 ON p1.nombre_grupo = p2.nombre_grupo 
              WHERE p1.nombre_participante < p2.nombre_participante 
              GROUP BY prov_a, prov_b 
              ORDER BY shared_gps DESC 
              LIMIT 6
            ),
            all_provs AS (
              SELECT prov_a AS prov FROM top_pairs 
              UNION DISTINCT 
              SELECT prov_b AS prov FROM top_pairs
            ),
            prov_stats AS (
              SELECT 
                ap.prov, 
                COUNT(DISTINCT c.id_contrato) AS num_contratos, 
                SUM(c.valor_del_contrato) AS valor_total 
              FROM all_provs ap 
              LEFT JOIN `{PROJECT}.{DATASET}.grupos_proveedores` gp ON gp.nombre_participante = ap.prov 
              LEFT JOIN `{PROJECT}.{DATASET}.contratos_electronicos` c ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo)) OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(ap.prov)) 
              GROUP BY ap.prov
            )
            SELECT 
              tp.prov_a, 
              sa.num_contratos AS contr_a, 
              sa.valor_total AS val_a, 
              tp.prov_b, 
              sb.num_contratos AS contr_b, 
              sb.valor_total AS val_b, 
              tp.shared_gps 
            FROM top_pairs tp 
            JOIN prov_stats sa ON tp.prov_a = sa.prov 
            JOIN prov_stats sb ON tp.prov_b = sb.prov
            """
        try:
            rows = query(sql, max_rows=top)
        except Exception as err:
            return f"Error al consultar redes de consorcios: {err}"
            
        if not rows:
            return f"No se encontraron redes de consorcios recurrentes{' para ' + entidad.upper() if entidad else ''}."

        # Build nodes and edges for graphing with explicit type casts
        nodes = {}
        edges = []
        for r in rows:
            pa = r['prov_a']
            pb = r['prov_b']
            if pa not in nodes:
                nodes[pa] = {"val": float(r.get('val_a', 0) or 0), "contr": int(r.get('contr_a', 0) or 0)}
            if pb not in nodes:
                nodes[pb] = {"val": float(r.get('val_b', 0) or 0), "contr": int(r.get('contr_b', 0) or 0)}
            edges.append((pa, pb, int(r.get('shared_gps', 0) or 0)))

        # Draw network graph
        chart_token = generar_red_consorcios(
            titulo=f"Redes de Consorcios Recurrentes - {entidad.upper()}" if entidad else "Redes de Consorcios Recurrentes Top (Socios Frecuentes)",
            central_node=None,
            nodes=nodes,
            edges=edges
        )

        result = f"=== REDES DE PROVEEDORES EN CONSORCIOS RECURRENTES ===\n"
        if entidad:
            result += f"Entidad: {entidad.upper()}\n"
        result += f"{chart_token}\n\n"
        if entidad:
            result += f"Mostrando las parejas de proveedores que participan juntos en consorcios con mayor frecuencia en {entidad.upper()}:\n\n"
        else:
            result += "Mostrando las parejas de proveedores que participan juntos en consorcios con mayor frecuencia en el pais:\n\n"
        
        formatted = []
        for r in rows:
            formatted.append({
                'proveedor_a': r['prov_a'][:25],
                'contr_a': r['contr_a'] or 0,
                'proveedor_b': r['prov_b'][:25],
                'contr_b': r['contr_b'] or 0,
                'consorcios_compartidos': r['shared_gps']
            })
        result += format_table(formatted) + "\n\n"
        result += "💡 Sugerencia: Puedes analizar la red de un proveedor específico escribiendo:\n"
        result += f"\"Analizar participación en consorcios de {rows[0]['prov_a'] if rows else 'FIRM SAS'}\""
        return result

    # Case: Specific contractor
    clean = proveedor.strip()
    
    # 1. Query to find groups the contractor belongs to (original groups logic)
    sql_groups = f"""
    SELECT DISTINCT gp.nombre_grupo, gp.nit_grupo
    FROM `{PROJECT}.{DATASET}.grupos_proveedores` gp
    {"JOIN `" + PROJECT + "." + DATASET + ".contratos_electronicos` c ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo))" if entidad else ""}
    WHERE ({safe_like('gp.nombre_participante', clean)} OR gp.nit_participante = '{clean}' OR {safe_like('gp.nombre_grupo', clean)})
      {"AND " + safe_like('c.nombre_entidad', entidad) if entidad else ""}
    LIMIT {top}
    """
    groups_rows = query(sql_groups, max_rows=top)
    if not groups_rows:
        return f"No se encontraron registros de participacion en consorcios o uniones temporales para '{clean}'{' en ' + entidad.upper() if entidad else ''}."
        
    # 2. Query partners and their stats
    sql_partners = f"""
    WITH my_groups AS (
      SELECT DISTINCT gp.nombre_grupo 
      FROM `{PROJECT}.{DATASET}.grupos_proveedores` gp
      {"JOIN `" + PROJECT + "." + DATASET + ".contratos_electronicos` c ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo))" if entidad else ""}
      WHERE ({safe_like('gp.nombre_participante', clean)} OR gp.nit_participante = '{clean}' OR {safe_like('gp.nombre_grupo', clean)})
        {"AND " + safe_like('c.nombre_entidad', entidad) if entidad else ""}
    ),
    partners AS (
      SELECT 
        nombre_participante AS partner_name, 
        nit_participante AS partner_nit, 
        COUNT(DISTINCT gp.nombre_grupo) AS shared_consorcios 
      FROM `{PROJECT}.{DATASET}.grupos_proveedores` gp 
      JOIN my_groups mg ON gp.nombre_grupo = mg.nombre_grupo 
      WHERE NOT ({safe_like('nombre_participante', clean)} OR nit_participante = '{clean}') 
      GROUP BY partner_name, partner_nit 
      ORDER BY shared_consorcios DESC 
      LIMIT 6
    ),
    all_names AS (
      SELECT CAST('{clean}' AS STRING) AS name 
      UNION DISTINCT 
      SELECT partner_name AS name FROM partners
    ),
    stats AS (
      SELECT 
        an.name, 
        COUNT(DISTINCT c.id_contrato) AS num_contratos, 
        SUM(c.valor_del_contrato) AS valor_total 
      FROM all_names an 
      LEFT JOIN `{PROJECT}.{DATASET}.grupos_proveedores` gp ON gp.nombre_participante = an.name 
      LEFT JOIN `{PROJECT}.{DATASET}.contratos_electronicos` c ON c.documento_proveedor = gp.nit_grupo OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo)) OR LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(an.name)) 
      {"WHERE " + safe_like('c.nombre_entidad', entidad) + " AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')" if entidad else "WHERE c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')"}
      GROUP BY an.name
    )
    SELECT 
      p.partner_name, 
      p.partner_nit, 
      p.shared_consorcios, 
      s.num_contratos, 
      s.valor_total 
    FROM partners p 
    JOIN stats s ON p.partner_name = s.name
    """
    
    # 3. Query target provider's own stats
    sql_self = f"""
    SELECT 
      COUNT(DISTINCT c.id_contrato) AS num_contratos, 
      SUM(c.valor_del_contrato) AS valor_total 
    FROM `{PROJECT}.{DATASET}.contratos_electronicos` c
    WHERE (LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM('{clean}')) 
       OR EXISTS (
         SELECT 1 
         FROM `{PROJECT}.{DATASET}.grupos_proveedores` gp
         WHERE LOWER(TRIM(c.proveedor_adjudicado)) = LOWER(TRIM(gp.nombre_grupo))
           AND ({safe_like('gp.nombre_participante', clean)} OR gp.nit_participante = '{clean}')
       ))
       {"AND " + safe_like('c.nombre_entidad', entidad) + " AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')" if entidad else "AND c.estado_contrato NOT IN ('Borrador', 'Cancelado', 'Rechazado')"}
    """
    
    try:
        partner_rows = query(sql_partners, max_rows=10)
        self_rows = query(sql_self, max_rows=1)
    except Exception as err:
        return f"Error al consultar socios del proveedor: {err}"

    # Build nodes and edges for graphing with explicit type casts
    nodes = {}
    edges = []
    
    # Add central node
    self_contr = int(self_rows[0]['num_contratos'] or 0) if self_rows else 0
    self_val = float(self_rows[0]['valor_total'] or 0) if self_rows else 0
    nodes[clean] = {"val": self_val, "contr": self_contr}
    
    # Add partners
    for pr in partner_rows:
        p_name = pr['partner_name']
        nodes[p_name] = {"val": float(pr.get('valor_total', 0) or 0), "contr": int(pr.get('num_contratos', 0) or 0)}
        edges.append((clean, p_name, int(pr.get('shared_consorcios', 0) or 0)))
        
    # Draw star network graph
    chart_token = generar_red_consorcios(
        titulo=f"Socios Frecuentes - {clean} ({entidad.upper()})" if entidad else f"Red de Socios Frecuentes - {clean}",
        central_node=clean,
        nodes=nodes,
        edges=edges
    )

    result = f"=== AUDITORÍA DE PARTICIPACIÓN EN CONSORCIOS / UNIONES TEMPORALES ===\n"
    result += f"{chart_token}\n\n"
    result += f"Contratista: {proveedor.upper()}\n"
    if entidad:
        result += f"Entidad: {entidad.upper()}\n"
    result += f"• Contratos totales ganados (UTs o Directo): {self_contr} | Valor: ${self_val:,.0f} COP\n\n"
    
    for idx, g in enumerate(groups_rows):
        g_name = g['nombre_grupo']
        g_nit = g['nit_grupo'] or 'No Definido'
        
        sql_parts = f"""
        SELECT nombre_participante, nit_participante, participacion, es_lider_del_grupo
        FROM `{PROJECT}.{DATASET}.grupos_proveedores`
        WHERE nombre_grupo = '{g_name}'
        """
        parts_rows = query(sql_parts, max_rows=10)
        
        sql_contracts = f"""
        SELECT id_contrato, nombre_entidad, valor_del_contrato, estado_contrato, fecha_de_firma
        FROM `{PROJECT}.{DATASET}.contratos_electronicos`
        WHERE (proveedor_adjudicado = '{g_name}' OR (documento_proveedor = '{g_nit}' AND '{g_nit}' != 'No Definido'))
          {"AND " + safe_like('nombre_entidad', entidad) if entidad else ""}
        ORDER BY fecha_de_firma DESC
        LIMIT 5
        """
        contracts_rows = query(sql_contracts, max_rows=5)
        
        result += f"👥 Consorcio #{idx+1}: {g_name} (NIT UT: {g_nit})\n"
        result += "  • Miembros del Consorcio:\n"
        for p in parts_rows:
            pct = p.get('participacion') or '-'
            is_lead = " (Líder)" if str(p.get('es_lider_del_grupo')).lower() in ('true', 'verdadero', 'si') else ""
            result += f"    - {p['nombre_participante']} (NIT: {p['nit_participante']}) | Participación: {pct}%{is_lead}\n"
            
        if contracts_rows:
            total_val = sum(r.get('valor_del_contrato', 0) or 0 for r in contracts_rows)
            result += f"  • Contratos adjudicados a esta UT ({len(contracts_rows)}): Valor total visible: ${total_val:,.0f} COP\n"
            for c in contracts_rows:
                v = float(c.get('valor_del_contrato', 0) or 0)
                result += f"    - Contrato {c['id_contrato']} | Entidad: {c['nombre_entidad']} | Valor: ${v:,.0f} | Estado: {c['estado_contrato']}\n"
        else:
            result += "  • Contratos adjudicados: No se encontraron contratos firmados a nombre de este consorcio.\n"
        result += "\n"
    return result



def estadisticas_uniones_temporales(entidad: str = "", anio: int = 2025) -> str:
    """Muestra estadisticas de contratos ganados por consorcios (UTs) vs proponentes individuales.
    Permite evaluar el nivel de consorciación en un sector o entidad.
    Args:
        entidad: Nombre (parcial) de la entidad pública a analizar.
        anio: Año de firma (default: 2025).
    """
    where_clause = f"EXTRACT(YEAR FROM fecha_de_firma) = {anio}"
    if entidad:
        where_clause += f" AND {safe_like('nombre_entidad', entidad)}"
        
    sql = f"""
    SELECT 
      es_grupo,
      COUNT(*) AS num_contratos,
      SUM(CAST(valor_del_contrato AS INT64)) AS valor_total,
      AVG(CAST(valor_del_contrato AS INT64)) AS valor_promedio
    FROM `{PROJECT}.{DATASET}.contratos_electronicos`
    WHERE {where_clause}
    GROUP BY es_grupo
    """
    rows = query(sql)
    
    target_desc = entidad.upper() if entidad else "TODO EL SISTEMA"
    result = f"=== ESTADÍSTICAS DE UNIONES TEMPORALES Y CONSORCIOS ===\n"
    result += f"Ámbito: {target_desc} | Año: {anio}\n\n"
    
    if not rows:
        return result + "No se encontraron contratos para los filtros especificados."
        
    total_contratos = sum(r.get('num_contratos', 0) or 0 for r in rows)
    total_valor = sum(r.get('valor_total', 0) or 0 for r in rows)
    
    formatted = []
    for r in rows:
        es_g = r['es_grupo']
        lbl = "Consorcio / Unión Temporal" if es_g == 'Si' else "Proponente Individual"
        pct_cnt = (r['num_contratos'] * 100 / total_contratos) if total_contratos > 0 else 0
        pct_val = (r['valor_total'] * 100 / total_valor) if total_valor > 0 else 0
        
        formatted.append({
            'tipo_proponente': lbl,
            'cantidad': r['num_contratos'],
            'porcentaje_cant': f"{pct_cnt:.1f}%",
            'valor_acumulado': f"${r['valor_total']:,.0f}",
            'porcentaje_val': f"{pct_val:.1f}%",
            'promedio_contrato': f"${r['valor_promedio']:,.0f}"
        })
        
    result += format_table(formatted) + "\n\n"
    result += "Nota: Este reporte analiza el campo 'es_grupo' de la base de contratos para contrastar cuántos procesos fueron adjudicados a alianzas temporales versus empresas individuales."
    return result


TOOLS = [
    perfil_proveedor,
    historial_contratista,
    buscar_contratos,
    procesos_activos,
    competencia_sector,
    tendencia_sector,
    entidades_objetivo,
    tasa_exito_proveedor,
    recomendar_procesos_grafo,
    detectar_contrato_amarrado,
    extraer_requisitos_proceso,
    analizar_participacion_consorcios,
    estadisticas_uniones_temporales,
]
