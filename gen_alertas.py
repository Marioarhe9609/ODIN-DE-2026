html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odin - Informe de Alertas Anticorrupcion</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a0f;--s:#12121a;--c:#1a1a2e;--b:rgba(255,255,255,.06);--t:#e4e4e7;--m:#71717a;--a:#818cf8;--g:#34d399;--o:#fb923c;--r:#f87171;--cy:#22d3ee}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:Inter,sans-serif;background:var(--bg);color:var(--t);line-height:1.6}
.c{max-width:960px;margin:0 auto;padding:0 24px}
.hero{padding:50px 0 30px;text-align:center}
.hero h1{font-size:30px;font-weight:800;letter-spacing:-1px;margin-bottom:8px;background:linear-gradient(180deg,#fff 30%,#a1a1aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:14px;color:var(--m);max-width:600px;margin:0 auto}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:rgba(129,140,248,.15);color:var(--a);margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--b);border-radius:12px;overflow:hidden;margin:24px 0}
.stat{background:var(--s);padding:18px;text-align:center}.stat b{font-size:24px;font-weight:800;letter-spacing:-1px}.stat small{display:block;font-size:11px;color:var(--m);font-weight:600;text-transform:uppercase;margin-top:2px}
.sec{margin:40px 0}.sec-l{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--a);margin-bottom:8px}
.sec-t{font-size:22px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}.sec-d{color:var(--m);font-size:13px;margin-bottom:18px}
.alert-card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:20px;margin:12px 0}
.alert-card h3{font-size:15px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.alert-card p{font-size:13px;color:var(--m);margin-bottom:10px}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;margin:2px}
.tag-r{background:rgba(248,113,113,.12);color:var(--r)}.tag-o{background:rgba(251,146,60,.12);color:var(--o)}
.tag-g{background:rgba(52,211,153,.12);color:var(--g)}.tag-cy{background:rgba(34,211,238,.12);color:var(--cy)}
.fields{margin-top:8px;padding:10px 14px;background:var(--c);border-radius:8px;font-size:12px;font-family:monospace;color:var(--m);line-height:1.8}
.fields b{color:var(--t)}
table{width:100%;border-collapse:collapse;font-size:12px;margin:12px 0}
thead{background:var(--c)}th{padding:10px;text-align:left;font-weight:600;color:var(--m);font-size:11px;text-transform:uppercase}
td{padding:8px 10px;border-top:1px solid var(--b)}
.ft{text-align:center;padding:30px 0;border-top:1px solid var(--b);margin-top:40px;font-size:12px;color:var(--m)}
@media(max-width:640px){.stats{grid-template-columns:1fr}}
</style></head><body><div class="c">

<div class="hero">
<div class="badge">Informe Tecnico - 8 mayo 2026</div>
<h1>Sistema de Alertas Anticorrupcion Odin</h1>
<p>25 alertas automatizadas basadas en 131M+ registros de SECOP II. Cada alerta detalla las tablas y campos exactos utilizados.</p>
</div>

<div class="stats">
<div class="stat"><b style="color:var(--r)">25</b><small>Alertas definidas</small></div>
<div class="stat"><b style="color:var(--a)">11</b><small>Tablas cruzadas</small></div>
<div class="stat"><b style="color:var(--g)">131M+</b><small>Registros analizados</small></div>
</div>

<!-- CAT 1 -->
<div class="sec">
<div class="sec-l">Categoria 1 - Riesgo Critico</div>
<div class="sec-t">Alertas de Corrupcion Directa</div>
<div class="sec-d">Senales que indican posible manipulacion del proceso de contratacion.</div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A01 - Proveedor Monopolista</h3>
<p>Proveedor que gana mas del 80% de contratos de una entidad en un periodo. Indica posible direccionamiento.</p>
<div class="fields">
<b>contratos_electronicos</b>: nombre_entidad, documento_proveedor, proveedor_adjudicado, valor_del_contrato, fecha_de_firma<br>
<b>proponentes_proceso</b>: id_procedimiento, nit_proveedor, entidad_compradora<br>
<b>SQL</b>: GROUP BY entidad + proveedor, HAVING count(*)/total > 0.8
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A02 - Fraccionamiento de Contratos</h3>
<p>Multiples contratos de minima cuantia al mismo proveedor que sumados superan el umbral de licitacion publica.</p>
<div class="fields">
<b>contratos_electronicos</b>: modalidad_de_contratacion, valor_del_contrato, documento_proveedor, nombre_entidad, fecha_de_firma<br>
<b>SQL</b>: WHERE modalidad = 'Minima Cuantia', GROUP BY entidad+proveedor+mes, HAVING SUM(valor) > umbral_licitacion
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A03 - Licitacion sin Competencia Real</h3>
<p>Procesos con un solo proponente o donde todos los demas se retiran.</p>
<div class="fields">
<b>procesos_contratacion</b>: id_del_proceso, modalidad_de_contratacion, proveedores_unicos_con_respuesta, precio_base<br>
<b>proponentes_proceso</b>: id_procedimiento, COUNT(DISTINCT nit_proveedor)<br>
<b>SQL</b>: WHERE proveedores_unicos_con_respuesta = 1 AND modalidad NOT IN ('Contratacion Directa')
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A04 - Red de Proveedores Fantasma</h3>
<p>Grupos/consorcios donde los mismos NITs aparecen repetidamente con diferentes nombres.</p>
<div class="fields">
<b>grupos_proveedores</b>: nit_participante, nombre_participante, nit_grupo, nombre_grupo, es_lider_del_grupo<br>
<b>contratos_electronicos</b>: es_grupo, documento_proveedor, valor_del_contrato<br>
<b>SQL</b>: GROUP BY nit_participante HAVING COUNT(DISTINCT nombre_grupo) > 3
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A05 - Proveedor Sancionado que Sigue Contratando</h3>
<p>Proveedores con multas o sanciones activas que reciben nuevos contratos.</p>
<div class="fields">
<b>multas_sanciones</b>: documento_proveedor, tipo_sanci_n, estado_sanci_n, fecha_sanci_n<br>
<b>contratos_electronicos</b>: documento_proveedor, fecha_de_firma, nombre_entidad, valor_del_contrato<br>
<b>SQL</b>: JOIN ON documento_proveedor WHERE fecha_firma > fecha_sancion
</div></div>
</div>

<!-- CAT 2 -->
<div class="sec">
<div class="sec-l">Categoria 2 - Riesgo Alto</div>
<div class="sec-t">Alertas de Sobrecostos y Adiciones</div>
<div class="sec-d">Patrones de incremento anormal en valor o plazo de contratos.</div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A06 - Adiciones Excesivas de Valor</h3>
<p>Contratos cuyo valor final supera el 50% del valor original por adiciones.</p>
<div class="fields">
<b>contratos_electronicos</b>: id_contrato, valor_del_contrato, nombre_entidad<br>
<b>adiciones</b>: id_contrato, tipo (='Valor'), descripcion, fecharegistro<br>
<b>SQL</b>: JOIN ON id_contrato, GROUP BY id_contrato, HAVING COUNT(tipo='Valor') > 2
</div></div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A07 - Suspensiones Repetidas</h3>
<p>Contratos con 3+ suspensiones que indican problemas de ejecucion o manipulacion de plazos.</p>
<div class="fields">
<b>suspensiones_contratos</b>: id_contrato, tipo, fecha_de_creacion, proposito_de_la_modificacion<br>
<b>contratos_electronicos</b>: id_contrato, nombre_entidad, proveedor_adjudicado, valor_del_contrato<br>
<b>SQL</b>: GROUP BY id_contrato HAVING COUNT(*) >= 3
</div></div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A08 - Modificaciones Masivas Post-Firma</h3>
<p>Contratos con mas de 5 modificaciones despues de firmados.</p>
<div class="fields">
<b>modificaciones_contratos</b>: id_contrato, tipo_modificacion, fecha_modificacion, valor_modificacion<br>
<b>contratos_electronicos</b>: id_contrato, valor_del_contrato, fecha_de_firma<br>
<b>SQL</b>: GROUP BY id_contrato HAVING COUNT(*) > 5
</div></div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A09 - Sobrecosto vs Precio Base</h3>
<p>Adjudicacion final que supera significativamente el precio base estimado.</p>
<div class="fields">
<b>procesos_contratacion</b>: id_del_proceso, precio_base, valor_total_adjudicacion<br>
<b>SQL</b>: WHERE valor_total_adjudicacion > precio_base * 1.3 AND precio_base > 0
</div></div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A10 - Contrato con Dias Adicionados Anomalos</h3>
<p>Contratos donde los dias adicionados superan la duracion original.</p>
<div class="fields">
<b>contratos_electronicos</b>: id_contrato, duracion_del_contrato, dias_adicionados, nombre_entidad, valor_del_contrato<br>
<b>SQL</b>: WHERE dias_adicionados > CAST(duracion_del_contrato AS INT64)
</div></div>
</div>

<!-- CAT 3 -->
<div class="sec">
<div class="sec-l">Categoria 3 - Seguimiento del Gasto</div>
<div class="sec-t">Alertas de Ejecucion Presupuestal</div>
<div class="sec-d">Monitoreo de la eficiencia y transparencia en la ejecucion del presupuesto publico.</div>

<div class="alert-card">
<h3><span class="tag tag-cy">GASTO</span> A11 - Baja Ejecucion Presupuestal</h3>
<p>Entidades con menos del 50% de ejecucion del presupuesto comprometido.</p>
<div class="fields">
<b>compromisos_presupuestales</b>: id_contrato, valor_item, balance_compromiso, referencia_contrato<br>
<b>contratos_electronicos</b>: codigo_entidad, nombre_entidad, valor_del_contrato, valor_pagado<br>
<b>SQL</b>: GROUP BY entidad, HAVING SUM(valor_pagado)/SUM(valor_contrato) < 0.5
</div></div>

<div class="alert-card">
<h3><span class="tag tag-cy">GASTO</span> A12 - CDP sin Contrato Asociado</h3>
<p>Certificados de disponibilidad presupuestal que nunca se vincularon a un contrato.</p>
<div class="fields">
<b>solicitudes_cdps</b>: id_contrato, id_proceso, entidad, saldo_total_a_comprometer, estado_del_contrato<br>
<b>SQL</b>: WHERE id_contrato IS NULL AND estado_del_contrato != 'Anulado'
</div></div>

<div class="alert-card">
<h3><span class="tag tag-cy">GASTO</span> A13 - Facturas sin Pago Confirmado</h3>
<p>Facturas radicadas hace mas de 60 dias sin confirmacion de pago.</p>
<div class="fields">
<b>facturas</b>: id_contrato, numero_de_factura, valor_total, fecha_factura, pago_confirmado, estado<br>
<b>SQL</b>: WHERE pago_confirmado = 'No' AND DATEDIFF(CURRENT_DATE, fecha_factura) > 60
</div></div>

<div class="alert-card">
<h3><span class="tag tag-cy">GASTO</span> A14 - Concentracion del Gasto en Contratacion Directa</h3>
<p>Entidades donde mas del 70% del presupuesto se ejecuta por contratacion directa.</p>
<div class="fields">
<b>contratos_electronicos</b>: nombre_entidad, modalidad_de_contratacion, valor_del_contrato<br>
<b>SQL</b>: GROUP BY entidad, HAVING SUM(CASE WHEN modalidad='Directa' THEN valor END)/SUM(valor) > 0.7
</div></div>

<div class="alert-card">
<h3><span class="tag tag-cy">GASTO</span> A15 - Pago Adelantado sin Amortizacion</h3>
<p>Contratos con pago adelantado donde el valor amortizado es cero despues de 90 dias.</p>
<div class="fields">
<b>contratos_electronicos</b>: id_contrato, valor_de_pago_adelantado, valor_amortizado, habilita_pago_adelantado, fecha_de_inicio_del_contrato<br>
<b>SQL</b>: WHERE habilita_pago_adelantado='Si' AND valor_amortizado=0 AND dias_desde_inicio > 90
</div></div>
</div>

<!-- CAT 4 -->
<div class="sec">
<div class="sec-l">Categoria 4 - Inteligencia de Mercado</div>
<div class="sec-t">Alertas de Competencia y Proveedores</div>
<div class="sec-d">Deteccion de patrones anomalos en el mercado de proveedores del Estado.</div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A16 - Proveedor en Multiples Departamentos</h3>
<p>Proveedor que gana contratos en 10+ departamentos simultaneamente (posible empresa fachada).</p>
<div class="fields">
<b>contratos_electronicos</b>: documento_proveedor, proveedor_adjudicado, departamento, COUNT(DISTINCT departamento)<br>
<b>SQL</b>: GROUP BY proveedor HAVING COUNT(DISTINCT departamento) > 10
</div></div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A17 - Proveedor Nuevo con Contratos Grandes</h3>
<p>Proveedores registrados hace menos de 6 meses que reciben contratos de alto valor.</p>
<div class="fields">
<b>contratos_electronicos</b>: documento_proveedor, fecha_de_firma, valor_del_contrato<br>
<b>grupos_proveedores</b>: nit_participante, fecha_creaci_n_participante<br>
<b>SQL</b>: WHERE DATEDIFF(fecha_firma, fecha_creacion) < 180 AND valor > percentil_90
</div></div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A18 - Misma Direccion Multiples Proveedores</h3>
<p>Varios proveedores registrados en la misma direccion fisica.</p>
<div class="fields">
<b>grupos_proveedores</b>: direcci_n_grupo, nit_grupo, nombre_grupo, departamento_grupo<br>
<b>SQL</b>: GROUP BY direccion HAVING COUNT(DISTINCT nit_grupo) > 3
</div></div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A19 - Proponentes que Siempre Pierden</h3>
<p>Proveedores que se presentan a 20+ procesos sin ganar ninguno (posibles oferentes de relleno).</p>
<div class="fields">
<b>proponentes_proceso</b>: nit_proveedor, proveedor, COUNT(id_procedimiento)<br>
<b>contratos_electronicos</b>: documento_proveedor (LEFT JOIN para verificar adjudicacion)<br>
<b>SQL</b>: GROUP BY nit_proveedor HAVING participaciones > 20 AND adjudicaciones = 0
</div></div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A20 - Concentracion Sectorial</h3>
<p>Sector donde 3 proveedores acumulan mas del 60% del valor contratado.</p>
<div class="fields">
<b>contratos_electronicos</b>: sector, documento_proveedor, valor_del_contrato<br>
<b>SQL</b>: RANK() OVER (PARTITION BY sector ORDER BY SUM(valor) DESC), top3/total > 0.6
</div></div>
</div>

<!-- CAT 5 -->
<div class="sec">
<div class="sec-l">Categoria 5 - Alertas Temporales</div>
<div class="sec-t">Patrones de Tiempo Anomalos</div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A21 - Contrato Firmado el Mismo Dia de Publicacion</h3>
<p>Procesos donde la firma ocurre en menos de 24h desde la publicacion.</p>
<div class="fields">
<b>procesos_contratacion</b>: id_del_proceso, fecha_de_publicacion_del_proceso<br>
<b>contratos_electronicos</b>: proceso_de_compra, fecha_de_firma<br>
<b>SQL</b>: WHERE DATEDIFF(fecha_firma, fecha_publicacion) < 1
</div></div>

<div class="alert-card">
<h3><span class="tag tag-o">ALTO</span> A22 - Contratos de Fin de Vigencia</h3>
<p>Explosion de contratos en los ultimos 15 dias del ano fiscal (gasto de panico).</p>
<div class="fields">
<b>contratos_electronicos</b>: fecha_de_firma, valor_del_contrato, nombre_entidad, modalidad_de_contratacion<br>
<b>SQL</b>: WHERE EXTRACT(MONTH FROM fecha_firma)=12 AND EXTRACT(DAY FROM fecha_firma) > 15
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A23 - Contrato Vencido sin Liquidar</h3>
<p>Contratos cuya fecha de fin paso hace mas de 180 dias y siguen sin liquidacion.</p>
<div class="fields">
<b>contratos_electronicos</b>: id_contrato, fecha_de_fin_del_contrato, liquidacion, estado_contrato, valor_pendiente_de_ejecucion<br>
<b>SQL</b>: WHERE fecha_fin < DATE_SUB(CURRENT, 180) AND liquidacion != 'Si' AND estado != 'Liquidado'
</div></div>

<div class="alert-card">
<h3><span class="tag tag-r">CRITICO</span> A24 - Facturacion Anticipada</h3>
<p>Facturas emitidas antes de la fecha de inicio del contrato.</p>
<div class="fields">
<b>facturas</b>: id_contrato, fecha_factura, valor_total<br>
<b>contratos_electronicos</b>: id_contrato, fecha_de_inicio_del_contrato<br>
<b>SQL</b>: JOIN ON id_contrato WHERE fecha_factura < fecha_inicio
</div></div>

<div class="alert-card">
<h3><span class="tag tag-g">MERCADO</span> A25 - Plan Anual vs Ejecucion Real</h3>
<p>Diferencias significativas entre lo planeado en el PAA y lo realmente contratado (requiere plan_anual cargado).</p>
<div class="fields">
<b>plan_anual_adquisiciones</b>: (pendiente de carga) codigo_unspsc, valor_estimado, entidad<br>
<b>contratos_electronicos</b>: codigo_de_categoria_principal, valor_del_contrato, nombre_entidad<br>
<b>SQL</b>: Comparar SUM(valor_estimado) vs SUM(valor_contrato) por entidad+categoria
</div></div>
</div>

<!-- RESUMEN -->
<div class="sec">
<div class="sec-l">Resumen de campos por tabla</div>
<div class="sec-t">Campos clave utilizados en las alertas</div>
<table><thead><tr><th>Tabla</th><th>Filas</th><th>Campos usados en alertas</th></tr></thead><tbody>
<tr><td><b>contratos_electronicos</b></td><td>5.6M</td><td>nombre_entidad, documento_proveedor, proveedor_adjudicado, valor_del_contrato, modalidad_de_contratacion, fecha_de_firma, fecha_de_inicio/fin, valor_pagado, valor_de_pago_adelantado, valor_amortizado, dias_adicionados, duracion_del_contrato, sector, departamento, estado_contrato, liquidacion, es_grupo, codigo_entidad, id_contrato, proceso_de_compra</td></tr>
<tr><td><b>procesos_contratacion</b></td><td>8.6M</td><td>id_del_proceso, precio_base, valor_total_adjudicacion, modalidad_de_contratacion, proveedores_unicos_con_respuesta, fecha_de_publicacion_del_proceso</td></tr>
<tr><td><b>proponentes_proceso</b></td><td>2.1M</td><td>id_procedimiento, nit_proveedor, proveedor, entidad_compradora, nit_entidad</td></tr>
<tr><td><b>facturas</b></td><td>40.5M</td><td>id_contrato, fecha_factura, valor_total, pago_confirmado, estado, numero_de_factura</td></tr>
<tr><td><b>adiciones</b></td><td>32.6M</td><td>id_contrato, tipo, descripcion, fecharegistro</td></tr>
<tr><td><b>modificaciones_contratos</b></td><td>11.4M</td><td>id_contrato, tipo_modificacion, fecha_modificacion, valor_modificacion</td></tr>
<tr><td><b>compromisos_presupuestales</b></td><td>10.8M</td><td>id_contrato, valor_item, balance_compromiso, referencia_contrato</td></tr>
<tr><td><b>solicitudes_cdps</b></td><td>18.9M</td><td>id_contrato, id_proceso, entidad, saldo_total_a_comprometer, estado_del_contrato</td></tr>
<tr><td><b>suspensiones_contratos</b></td><td>476K</td><td>id_contrato, tipo, fecha_de_creacion, proposito_de_la_modificacion</td></tr>
<tr><td><b>grupos_proveedores</b></td><td>578K</td><td>nit_participante, nombre_participante, nit_grupo, nombre_grupo, es_lider_del_grupo, direcci_n_grupo, fecha_creaci_n_participante</td></tr>
<tr><td><b>multas_sanciones</b></td><td>518</td><td>documento_proveedor, tipo_sanci_n, estado_sanci_n, fecha_sanci_n</td></tr>
</tbody></table>
</div>

<div class="ft">
<b>Odin v2</b> | Proyecto: odin-v2-495523 | 131M+ registros | Generado: 8 mayo 2026
</div>

</div></body></html>"""

with open("informe_alertas.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Informe generado: informe_alertas.html")
