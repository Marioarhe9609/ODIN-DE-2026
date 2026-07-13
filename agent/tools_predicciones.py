"""Odin v2 - Predictive analysis tools for public procurement spending."""
from agent.bq_client import query, PROJECT, DATASET
from agent.tools_graficos import generar_grafico_medidor

def predecir_demanda_unspsc(codigo: str, anio_proyeccion: int = 2026) -> str:
    """Predice la demanda de un código UNSPSC (compras y cantidad de contratos)
    para un año futuro mediante regresión lineal calculada en BigQuery.
    Args:
        codigo: Código UNSPSC o prefijo (ej: "432115").
        anio_proyeccion: Año para el cual realizar la proyección (ej: 2026).
    """
    sql = f"""
    WITH annual_data AS (
      SELECT
        EXTRACT(YEAR FROM fecha_de_firma) AS anio,
        COUNT(*) AS total_contratos,
        SUM(valor_del_contrato) AS total_valor
      FROM
        `{PROJECT}.{DATASET}.contratos_electronicos`
      WHERE
        (codigo_de_categoria_principal = '{codigo}' OR STARTS_WITH(codigo_de_categoria_principal, '{codigo}'))
        AND fecha_de_firma IS NOT NULL
        AND EXTRACT(YEAR FROM fecha_de_firma) BETWEEN 2018 AND 2025
      GROUP BY
        anio
    )
    SELECT
      anio,
      total_contratos,
      total_valor,
      (SELECT COVAR_POP(total_valor, anio) / NULLIF(VAR_POP(anio), 0) FROM annual_data) AS slope_valor,
      (SELECT AVG(total_valor) - (COVAR_POP(total_valor, anio) / NULLIF(VAR_POP(anio), 0)) * AVG(anio) FROM annual_data) AS intercept_valor,
      (SELECT COALESCE(CORR(total_valor, anio) * CORR(total_valor, anio), 0) FROM annual_data) AS r2_valor,
      (SELECT COVAR_POP(total_contratos, anio) / NULLIF(VAR_POP(anio), 0) FROM annual_data) AS slope_contratos,
      (SELECT AVG(total_contratos) - (COVAR_POP(total_contratos, anio) / NULLIF(VAR_POP(anio), 0)) * AVG(anio) FROM annual_data) AS intercept_contratos,
      (SELECT COALESCE(CORR(total_contratos, anio) * CORR(total_contratos, anio), 0) FROM annual_data) AS r2_contratos
    FROM
      annual_data
    ORDER BY
      anio ASC
    """
    
    rows = query(sql, max_rows=100)
    if not rows:
        return f"No se encontraron contratos históricos para la categoría UNSPSC '{codigo}'."
        
    if len(rows) < 2:
        r = rows[0]
        val_str = f"${r['total_valor']:,.0f}" if r['total_valor'] else "$0"
        return (f"Se encontraron datos históricos solo para el año {r['anio']}:\n"
                f"- Contratos: {r['total_contratos']}\n"
                f"- Valor total: {val_str} COP\n\n"
                f"⚠️ Se requieren al menos 2 años de datos históricos para proyectar tendencias.")

    r_sample = rows[0]
    slope_v = r_sample.get('slope_valor') or 0.0
    intercept_v = r_sample.get('intercept_valor') or 0.0
    r2_v = r_sample.get('r2_valor') or 0.0
    
    slope_c = r_sample.get('slope_contratos') or 0.0
    intercept_c = r_sample.get('intercept_contratos') or 0.0
    r2_c = r_sample.get('r2_contratos') or 0.0

    # Project values
    projected_val = max(0.0, slope_v * anio_proyeccion + intercept_v)
    projected_contr = max(0, int(round(slope_c * anio_proyeccion + intercept_c)))

    # Format historical rows for printing
    history_lines = []
    history_lines.append("Año | Contratos | Valor Total (COP)")
    history_lines.append("---|---|---")
    for r in rows:
        val_f = f"${r['total_valor']:,.0f}" if r['total_valor'] else "$0"
        history_lines.append(f"{r['anio']} | {r['total_contratos']:,} | {val_f}")

    proj_val_str = f"${projected_val:,.0f}"
    history_lines.append(f"**{anio_proyeccion} (PROYECTADO)** | **{projected_contr:,}** | **{proj_val_str}**")
    
    table_md = "\n".join(history_lines)

    # Use R2 for gauge chart of confidence
    confidence_score = float(r2_v * 100)
    gauge_marker = generar_grafico_medidor("Certeza de Predicción (R²)", confidence_score, 0, 100)

    # Create detailed text explanation
    trend_val_desc = "creciente" if slope_v > 0 else "decreciente"
    trend_contr_desc = "creciente" if slope_c > 0 else "decreciente"
    
    slope_v_str = f"${abs(slope_v):,.0f}"
    
    summary = (
        f"📊 **Análisis Predictivo de Demanda para UNSPSC '{codigo}'**\n\n"
        f"Hemos analizado el comportamiento histórico de contratación de la categoría UNSPSC **{codigo}** "
        f"entre los años 2018 y 2025 para proyectar la demanda en el año **{anio_proyeccion}**:\n\n"
        f"{table_md}\n\n"
        f"📈 **Detalles del Modelo Predictivo:**\n"
        f"- **Proyección de Gasto ({anio_proyeccion}):** Se proyecta un gasto total de {proj_val_str} COP. "
        f"La tendencia del gasto es **{trend_val_desc}** con un cambio promedio anual de {slope_v_str} COP.\n"
        f"- **Proyección de Volumen ({anio_proyeccion}):** Se proyecta la adjudicación de **{projected_contr:,}** contratos. "
        f"La tendencia en volumen de contratos es **{trend_contr_desc}** con un cambio promedio anual de {abs(slope_c):.1f} contratos.\n"
        f"- **Grado de Certeza ($R^2$):** {confidence_score:.1f}%. "
        f"Un valor cercano a 100% indica que la tendencia histórica es muy estable y predecible.\n\n"
        f"{gauge_marker}\n"
    )
    return summary


TOOLS = [predecir_demanda_unspsc]
