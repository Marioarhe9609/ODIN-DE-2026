html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odin v2 - Informe de Vistas Analiticas</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a0f;--s:#12121a;--c:#1a1a2e;--b:rgba(255,255,255,.06);--t:#e4e4e7;--m:#71717a;--a:#818cf8;--g:#34d399;--o:#fb923c;--r:#f87171;--cy:#22d3ee;--y:#facc15}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:Inter,sans-serif;background:var(--bg);color:var(--t);line-height:1.7}
.c{max-width:960px;margin:0 auto;padding:0 24px}
.hero{padding:50px 0 30px;text-align:center}
.hero h1{font-size:28px;font-weight:800;letter-spacing:-1px;margin-bottom:8px;background:linear-gradient(180deg,#fff 30%,#a1a1aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:14px;color:var(--m);max-width:600px;margin:0 auto}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:rgba(129,140,248,.15);color:var(--a);margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--b);border-radius:12px;overflow:hidden;margin:24px 0}
.stat{background:var(--s);padding:14px;text-align:center}.stat b{font-size:22px;font-weight:800}.stat small{display:block;font-size:10px;color:var(--m);font-weight:600;text-transform:uppercase;margin-top:2px}
.sec{margin:36px 0}.sec-l{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--a);margin-bottom:8px}
.sec-t{font-size:20px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}.sec-d{color:var(--m);font-size:13px;margin-bottom:14px}
.card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:18px;margin:10px 0}
.card h3{font-size:14px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.card p{font-size:12px;color:var(--m);margin-bottom:6px}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;margin:2px}
.tag-r{background:rgba(248,113,113,.12);color:var(--r)}.tag-o{background:rgba(251,146,60,.12);color:var(--o)}
.tag-g{background:rgba(52,211,153,.12);color:var(--g)}.tag-cy{background:rgba(34,211,238,.12);color:var(--cy)}
.tag-a{background:rgba(129,140,248,.12);color:var(--a)}.tag-y{background:rgba(250,204,21,.12);color:var(--y)}
table{width:100%;border-collapse:collapse;font-size:12px;margin:10px 0}
thead{background:var(--c)}th{padding:8px;text-align:left;font-weight:600;color:var(--m);font-size:10px;text-transform:uppercase}
td{padding:7px 8px;border-top:1px solid var(--b)}
code{font-family:'JetBrains Mono',monospace;background:var(--c);padding:2px 6px;border-radius:4px;font-size:11px}
.check{color:var(--g)}.cross{color:var(--r)}.warn{color:var(--o)}
.ft{text-align:center;padding:30px 0;border-top:1px solid var(--b);margin-top:40px;font-size:12px;color:var(--m)}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
</style></head><body><div class="c">

<div class="hero">
<div class="badge">Fase 2 Completada - 11 mayo 2026</div>
<h1>Vistas Analiticas en BigQuery</h1>
<p>22 vistas creadas sobre 12 tablas con 149M+ registros. Informe de cobertura y validacion de 5 banderas rojas adicionales.</p>
</div>

<div class="stats">
<div class="stat"><b style="color:var(--g)">22</b><small>Vistas creadas</small></div>
<div class="stat"><b style="color:var(--r)">11</b><small>Anticorrupcion</small></div>
<div class="stat"><b style="color:var(--cy)">6</b><small>Gasto Publico</small></div>
<div class="stat"><b style="color:var(--g)">5</b><small>Mercado</small></div>
</div>

<!-- VISTAS EXISTENTES -->
<div class="sec">
<div class="sec-l" style="color:var(--r)">MCP Anticorrupcion</div>
<div class="sec-t">11 vistas de deteccion de riesgos</div>
<table><thead><tr><th>Vista</th><th>Alerta</th><th>Que detecta</th></tr></thead><tbody>
<tr><td><code>v_anticorr_monopolista</code></td><td><span class="tag tag-r">A01</span></td><td>Proveedores con >80% de contratos en una entidad. Agrupa por entidad+proveedor con % y valores.</td></tr>
<tr><td><code>v_anticorr_fraccionamiento</code></td><td><span class="tag tag-r">A02</span></td><td>Minimas cuantias al mismo proveedor que sumadas superan umbral. Agrupa por entidad+proveedor+mes.</td></tr>
<tr><td><code>v_anticorr_sin_competencia</code></td><td><span class="tag tag-r">A03</span></td><td>Procesos competitivos (no directa) adjudicados con 1 solo proponente.</td></tr>
<tr><td><code>v_anticorr_sancionado_activo</code></td><td><span class="tag tag-r">A05</span></td><td>Cruce multas_sanciones x contratos: proveedor sancionado con contratos posteriores.</td></tr>
<tr><td><code>v_anticorr_adiciones</code></td><td><span class="tag tag-o">A06</span></td><td>Contratos con 3+ adiciones. Cuenta adiciones de valor y de plazo por separado.</td></tr>
<tr><td><code>v_anticorr_suspensiones</code></td><td><span class="tag tag-o">A07</span></td><td>Contratos con 3+ suspensiones. Incluye propositos concatenados.</td></tr>
<tr><td><code>v_anticorr_modificaciones</code></td><td><span class="tag tag-o">A08</span></td><td>Contratos con >5 modificaciones post-firma.</td></tr>
<tr><td><code>v_anticorr_sobrecosto</code></td><td><span class="tag tag-o">A09</span></td><td>Adjudicaciones que superan +30% el precio base del proceso.</td></tr>
<tr><td><code>v_anticorr_concentracion_directa</code></td><td><span class="tag tag-o">A14</span></td><td>Entidades con >70% del gasto en contratacion directa.</td></tr>
<tr><td><code>v_anticorr_vencidos</code></td><td><span class="tag tag-r">A23</span></td><td>Contratos vencidos hace >180 dias sin liquidar. Calcula dias_vencido.</td></tr>
<tr><td><code>v_anticorr_sobrefacturacion</code></td><td><span class="tag tag-r">A24</span></td><td>Cruce facturas x contratos: total facturado > valor del contrato (+10%).</td></tr>
</tbody></table>
</div>

<div class="sec">
<div class="sec-l" style="color:var(--cy)">MCP Gasto Publico</div>
<div class="sec-t">6 vistas de reporteria y analisis</div>
<table><thead><tr><th>Vista</th><th>Tipo</th><th>Que genera</th></tr></thead><tbody>
<tr><td><code>v_gasto_ejecucion_entidad</code></td><td><span class="tag tag-cy">REPORTE</span></td><td>Tabla asignado vs pagado vs pendiente por entidad/depto/anio. Calcula % ejecucion.</td></tr>
<tr><td><code>v_gasto_por_modalidad</code></td><td><span class="tag tag-a">ANALISIS</span></td><td>Distribucion del gasto por modalidad de contratacion y entidad.</td></tr>
<tr><td><code>v_gasto_temporal</code></td><td><span class="tag tag-a">ANALISIS</span></td><td>Evolucion mensual del gasto por entidad/depto.</td></tr>
<tr><td><code>v_gasto_cdps</code></td><td><span class="tag tag-cy">REPORTE</span></td><td>Resumen CDPs: comprometido vs utilizado vs saldo. CDPs sin contrato.</td></tr>
<tr><td><code>v_gasto_flujo_pagos</code></td><td><span class="tag tag-cy">REPORTE</span></td><td>Cruce facturas x contratos: total facturado, pagado, pendiente por contrato.</td></tr>
<tr><td><code>v_gasto_compromisos</code></td><td><span class="tag tag-cy">REPORTE</span></td><td>Balance de compromisos presupuestales: comprometido vs liberado.</td></tr>
</tbody></table>
</div>

<div class="sec">
<div class="sec-l" style="color:var(--g)">MCP Mercado</div>
<div class="sec-t">5 vistas de inteligencia de mercado</div>
<table><thead><tr><th>Vista</th><th>Tipo</th><th>Que genera</th></tr></thead><tbody>
<tr><td><code>v_mercado_perfil_proveedor</code></td><td><span class="tag tag-cy">REPORTE</span></td><td>Radiografia: total contratos, valor, entidades, departamentos, sectores por proveedor.</td></tr>
<tr><td><code>v_mercado_competencia_sector</code></td><td><span class="tag tag-a">ANALISIS</span></td><td>Top proveedores por categoria UNSPSC con % de mercado.</td></tr>
<tr><td><code>v_mercado_tendencia_sector</code></td><td><span class="tag tag-a">ANALISIS</span></td><td>Evolucion trimestral del gasto por sector: creciendo o decreciendo?</td></tr>
<tr><td><code>v_mercado_entidades_objetivo</code></td><td><span class="tag tag-g">PREDICT</span></td><td>Entidades que mas compran por UNSPSC: patrones de compra.</td></tr>
<tr><td><code>v_mercado_tasa_exito</code></td><td><span class="tag tag-g">PREDICT</span></td><td>Tasa de exito: participaciones vs adjudicaciones por proveedor.</td></tr>
</tbody></table>
</div>

<!-- 5 BANDERAS ROJAS -->
<div class="sec">
<div class="sec-l" style="color:var(--y)">Validacion de 5 banderas rojas nuevas</div>
<div class="sec-t">Disponibilidad de datos por bandera</div>

<!-- BANDERA 1 -->
<div class="card">
<h3><span class="tag tag-g">DATOS OK</span> 1. Suma acumulada de adiciones</h3>
<p>Verificar contratos donde la suma de adiciones incrementa significativamente el valor original.</p>
<table><thead><tr><th>Campo</th><th>Tabla</th><th>Estado</th></tr></thead><tbody>
<tr><td><code>id_contrato</code></td><td>adiciones (32.6M rows)</td><td class="check">Disponible</td></tr>
<tr><td><code>tipo</code></td><td>adiciones - valores: MODIFICACION GENERAL, etc</td><td class="check">Disponible</td></tr>
<tr><td><code>descripcion</code></td><td>adiciones - texto libre con detalle</td><td class="check">Disponible</td></tr>
<tr><td><code>valor_del_contrato</code></td><td>contratos_electronicos (JOIN)</td><td class="check">Disponible</td></tr>
</tbody></table>
<p><b>Vista existente:</b> <code>v_anticorr_adiciones</code> ya cubre esto. Se puede mejorar con SUM del valor de cada adicion cruzando con valor original.</p>
<p><b>Accion:</b> <span class="tag tag-g">Listo</span> Solo necesita ajuste menor para calcular % acumulado de incremento.</p>
</div>

<!-- BANDERA 2 -->
<div class="card">
<h3><span class="tag tag-g">DATOS OK</span> 2. Contratacion directa recurrente (sin OPS)</h3>
<p>Entidades que usan contratacion directa de forma sistematica excluyendo Prestacion de Servicios (OPS).</p>
<table><thead><tr><th>Campo</th><th>Tabla</th><th>Estado</th></tr></thead><tbody>
<tr><td><code>modalidad_de_contratacion</code></td><td>contratos_electronicos</td><td class="check">Disponible - 'Contratacion Directa'</td></tr>
<tr><td><code>tipo_de_contrato</code></td><td>contratos_electronicos</td><td class="check">Disponible - 'Prestacion de servicios' = 4.1M contratos directos</td></tr>
<tr><td><code>nombre_entidad</code></td><td>contratos_electronicos</td><td class="check">Disponible</td></tr>
</tbody></table>
<p><b>Distribucion directa SIN OPS:</b></p>
<table><thead><tr><th>Tipo (no OPS)</th><th>Contratos</th></tr></thead><tbody>
<tr><td>Otro</td><td>129,435</td></tr>
<tr><td>Arrendamiento de inmuebles</td><td>44,457</td></tr>
<tr><td>Comodato</td><td>12,816</td></tr>
<tr><td>Obra</td><td>11,555</td></tr>
<tr><td>Compraventa</td><td>5,946</td></tr>
<tr><td>Suministros</td><td>5,115</td></tr>
</tbody></table>
<p><b>Vista existente:</b> <code>v_anticorr_concentracion_directa</code> necesita filtro adicional: <code>WHERE tipo_de_contrato NOT LIKE '%restaci%'</code></p>
<p><b>Accion:</b> <span class="tag tag-o">Crear nueva vista</span> <code>v_anticorr_directa_sin_ops</code></p>
</div>

<!-- BANDERA 3 -->
<div class="card">
<h3><span class="tag tag-g">DATOS OK</span> 3. Consulta publica</h3>
<p>Procesos en etapa de consulta publica / publicados abiertos a observaciones.</p>
<table><thead><tr><th>Campo</th><th>Tabla</th><th>Estado</th></tr></thead><tbody>
<tr><td><code>estado_del_procedimiento</code></td><td>procesos_contratacion (8.6M rows)</td><td class="check">Disponible</td></tr>
<tr><td><code>fecha_de_publicacion_del_proceso</code></td><td>procesos_contratacion</td><td class="check">Disponible</td></tr>
<tr><td><code>modalidad_de_contratacion</code></td><td>procesos_contratacion</td><td class="check">Disponible</td></tr>
</tbody></table>
<p><b>Estados disponibles:</b> Publicado (2.5M), Evaluacion (522K), Abierto (32K), Borrador (43K)</p>
<p><b>Accion:</b> <span class="tag tag-o">Crear nueva vista</span> <code>v_mercado_consulta_publica</code> para procesos en estado 'Publicado' o 'Abierto'</p>
</div>

<!-- BANDERA 4 -->
<div class="card">
<h3><span class="tag tag-g">DATOS OK</span> 4. Mismos postulantes a diferentes contratos (mismo grupo)</h3>
<p>Detectar cuando el mismo grupo de empresas se postula junta repetidamente a distintos procesos.</p>
<table><thead><tr><th>Campo</th><th>Tabla</th><th>Estado</th></tr></thead><tbody>
<tr><td><code>id_procedimiento</code></td><td>proponentes_proceso (2.1M rows)</td><td class="check">Disponible</td></tr>
<tr><td><code>nit_proveedor</code></td><td>proponentes_proceso</td><td class="check">Disponible</td></tr>
<tr><td><code>proveedor</code></td><td>proponentes_proceso (nombre)</td><td class="check">Disponible</td></tr>
<tr><td><code>entidad_compradora</code></td><td>proponentes_proceso</td><td class="check">Disponible</td></tr>
</tbody></table>
<p><b>Logica:</b> Agrupar proponentes por proceso, crear un "fingerprint" del grupo (SET de NITs ordenados), luego contar en cuantos procesos aparece el mismo fingerprint.</p>
<p><b>Accion:</b> <span class="tag tag-o">Crear nueva vista</span> <code>v_anticorr_grupos_postulantes</code></p>
</div>

<!-- BANDERA 5 -->
<div class="card">
<h3><span class="tag tag-y">DATOS PARCIALES</span> 5. Coincidencias por representante legal, telefono, correo, direccion</h3>
<p>Proveedores distintos que comparten representante legal, telefono, correo o direccion fisica.</p>
<table><thead><tr><th>Campo</th><th>Tabla</th><th>Estado</th></tr></thead><tbody>
<tr><td><code>nombre_representante_legal</code></td><td>contratos_electronicos</td><td class="check">Disponible</td></tr>
<tr><td><code>identificacion_representante_legal</code></td><td>contratos_electronicos</td><td class="check">Disponible</td></tr>
<tr><td><code>domicilio_representante_legal</code></td><td>contratos_electronicos</td><td class="check">Disponible</td></tr>
<tr><td><code>nombre_representante_legal_grupo</code></td><td>grupos_proveedores</td><td class="check">Disponible</td></tr>
<tr><td><code>numero_doc_representante_legal_grupo</code></td><td>grupos_proveedores</td><td class="check">Disponible</td></tr>
<tr><td><code>correo_representante_legal_grupo</code></td><td>grupos_proveedores</td><td class="check">Disponible</td></tr>
<tr><td><code>telefono_representante_legal_grupo</code></td><td>grupos_proveedores</td><td class="check">Disponible</td></tr>
<tr><td><code>correo_electronico_grupo</code></td><td>grupos_proveedores</td><td class="check">Disponible</td></tr>
<tr><td>Telefono proveedor</td><td>contratos_electronicos</td><td class="cross">NO existe campo telefono/celular</td></tr>
<tr><td>Correo proveedor</td><td>contratos_electronicos</td><td class="cross">NO existe campo correo proveedor</td></tr>
<tr><td>Direccion proveedor</td><td>contratos_electronicos</td><td class="cross">NO existe - solo domicilio del rep. legal</td></tr>
</tbody></table>
<p><b>Cobertura:</b></p>
<table><thead><tr><th>Dato</th><th>Fuente principal</th><th>Cruce posible</th></tr></thead><tbody>
<tr><td>Representante legal</td><td>contratos (nombre + cedula)</td><td class="check">Multiples NITs con mismo rep legal</td></tr>
<tr><td>Telefono</td><td>grupos_proveedores (telefono_rep)</td><td class="check">Distintos grupos con mismo telefono</td></tr>
<tr><td>Correo</td><td>grupos_proveedores (correo_grupo + correo_rep)</td><td class="check">Distintos NITs con mismo correo</td></tr>
<tr><td>Direccion</td><td>contratos (domicilio_rep) + plan_anual (contacto)</td><td class="warn">Parcial - solo domicilio del rep. legal</td></tr>
<tr><td>Celular</td><td>Ninguna tabla</td><td class="cross">No disponible en SECOP II</td></tr>
</tbody></table>
<p><b>Accion:</b> <span class="tag tag-o">Crear 3 vistas</span> <code>v_anticorr_mismo_replegal</code>, <code>v_anticorr_mismo_correo</code>, <code>v_anticorr_mismo_telefono</code></p>
</div>
</div>

<!-- RESUMEN -->
<div class="sec">
<div class="sec-l">Resumen de acciones</div>
<div class="sec-t">Proximos pasos para las 5 banderas</div>
<table><thead><tr><th>#</th><th>Bandera</th><th>Datos</th><th>Accion</th></tr></thead><tbody>
<tr><td>1</td><td>Adiciones acumuladas</td><td class="check">100%</td><td>Ajustar vista existente con % acumulado</td></tr>
<tr><td>2</td><td>Directa sin OPS</td><td class="check">100%</td><td>Crear <code>v_anticorr_directa_sin_ops</code></td></tr>
<tr><td>3</td><td>Consulta publica</td><td class="check">100%</td><td>Crear <code>v_mercado_consulta_publica</code></td></tr>
<tr><td>4</td><td>Mismo grupo postulantes</td><td class="check">100%</td><td>Crear <code>v_anticorr_grupos_postulantes</code></td></tr>
<tr><td>5</td><td>Coincidencias contacto</td><td class="warn">~75%</td><td>Crear 3 vistas (rep legal, correo, tel). Celular no disponible en SECOP.</td></tr>
</tbody></table>
</div>

<div class="ft">
<b>Odin v2</b> | Informe de Vistas Analiticas | BigQuery: odin-v2-495523 | 11 mayo 2026
</div>

</div></body></html>"""

with open("docs/informe_vistas.html", "w", encoding="utf-8") as f:
    f.write(html)
print("OK: docs/informe_vistas.html")
