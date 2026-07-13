html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odin v2 - Arquitectura de Agentes</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a0f;--s:#12121a;--c:#1a1a2e;--b:rgba(255,255,255,.06);--t:#e4e4e7;--m:#71717a;--a:#818cf8;--g:#34d399;--o:#fb923c;--r:#f87171;--cy:#22d3ee;--y:#facc15}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:Inter,sans-serif;background:var(--bg);color:var(--t);line-height:1.7}
.c{max-width:960px;margin:0 auto;padding:0 24px}
.hero{padding:50px 0 30px;text-align:center;position:relative}
.hero::before{content:'';position:absolute;top:-80px;left:50%;transform:translateX(-50%);width:500px;height:300px;background:radial-gradient(ellipse,rgba(129,140,248,.12),transparent 70%);pointer-events:none}
.hero h1{font-size:30px;font-weight:800;letter-spacing:-1px;margin-bottom:8px;background:linear-gradient(180deg,#fff 30%,#a1a1aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:14px;color:var(--m);max-width:600px;margin:0 auto}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:rgba(129,140,248,.15);color:var(--a);margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--b);border-radius:12px;overflow:hidden;margin:24px 0}
.stat{background:var(--s);padding:16px;text-align:center}.stat b{font-size:22px;font-weight:800;letter-spacing:-1px}.stat small{display:block;font-size:10px;color:var(--m);font-weight:600;text-transform:uppercase;margin-top:2px}
.sec{margin:40px 0}.sec-l{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--a);margin-bottom:8px}
.sec-t{font-size:22px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}.sec-d{color:var(--m);font-size:13px;margin-bottom:18px}
.card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:20px;margin:12px 0}
.card h3{font-size:15px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.card p{font-size:13px;color:var(--m);margin-bottom:10px}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;margin:2px}
.tag-r{background:rgba(248,113,113,.12);color:var(--r)}.tag-o{background:rgba(251,146,60,.12);color:var(--o)}
.tag-g{background:rgba(52,211,153,.12);color:var(--g)}.tag-cy{background:rgba(34,211,238,.12);color:var(--cy)}
.tag-a{background:rgba(129,140,248,.12);color:var(--a)}.tag-y{background:rgba(250,204,21,.12);color:var(--y)}
table{width:100%;border-collapse:collapse;font-size:12px;margin:12px 0}
thead{background:var(--c)}th{padding:10px;text-align:left;font-weight:600;color:var(--m);font-size:11px;text-transform:uppercase}
td{padding:8px 10px;border-top:1px solid var(--b)}
code{font-family:'JetBrains Mono',monospace;background:var(--c);padding:2px 6px;border-radius:4px;font-size:11px}
pre{background:var(--c);border-radius:10px;padding:16px;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.6;overflow-x:auto;margin:12px 0;border:1px solid var(--b)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.q-card{background:var(--c);border:1px solid rgba(250,204,21,.15);border-radius:12px;padding:16px;margin:10px 0}
.q-card b{color:var(--y);font-size:13px}.q-card p{font-size:12px;color:var(--m);margin-top:4px}
.ft{text-align:center;padding:30px 0;border-top:1px solid var(--b);margin-top:40px;font-size:12px;color:var(--m)}
@media(max-width:700px){.stats{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}}
</style></head><body><div class="c">

<div class="hero">
<div class="badge">Arquitectura Tecnica - 8 mayo 2026</div>
<h1>Odin v2 - Sistema de Agentes</h1>
<p>Arquitectura basada en MCP + Gemini 2.5 Pro para consultar 131M+ registros de SECOP II via chat con graficos y grafos.</p>
</div>

<div class="stats">
<div class="stat"><b style="color:var(--a)">3</b><small>MCP Servers</small></div>
<div class="stat"><b style="color:var(--g)">20</b><small>Tools / Herramientas</small></div>
<div class="stat"><b style="color:var(--cy)">11</b><small>Tablas BigQuery</small></div>
<div class="stat"><b style="color:var(--o)">131M+</b><small>Registros</small></div>
</div>

<!-- DIAGRAMA -->
<div class="sec">
<div class="sec-l">Vista general</div>
<div class="sec-t">Diagrama de arquitectura</div>
<div class="sec-d">Flujo completo: usuario envia mensaje por Telegram/WhatsApp, el gateway lo pasa al agente orquestador, este decide que herramientas MCP usar, consulta BigQuery, genera graficos y devuelve la respuesta.</div>

<div style="background:var(--s);border:1px solid var(--b);border-radius:14px;padding:24px;overflow-x:auto">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:900px;margin:0 auto;display:block">

<!-- Canal: Telegram -->
<rect x="30" y="20" width="130" height="50" rx="10" fill="#1a1a2e" stroke="#818cf8" stroke-width="1.5"/>
<text x="95" y="42" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">Telegram Bot</text>
<text x="95" y="57" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">MVP Canal</text>

<!-- Canal: WhatsApp -->
<rect x="180" y="20" width="130" height="50" rx="10" fill="#1a1a2e" stroke="#818cf8" stroke-width="1.5"/>
<text x="245" y="42" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">WhatsApp API</text>
<text x="245" y="57" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">Fase 2</text>

<!-- Canal: Web -->
<rect x="330" y="20" width="130" height="50" rx="10" fill="#1a1a2e" stroke="#818cf8" stroke-width="1.5" stroke-dasharray="4"/>
<text x="395" y="42" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">Web Chat</text>
<text x="395" y="57" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">Futuro</text>

<!-- Flechas al gateway -->
<line x1="95" y1="70" x2="250" y2="100" stroke="#818cf8" stroke-width="1"/>
<line x1="245" y1="70" x2="250" y2="100" stroke="#818cf8" stroke-width="1"/>
<line x1="395" y1="70" x2="250" y2="100" stroke="#818cf8" stroke-width="1" stroke-dasharray="4"/>

<!-- Gateway -->
<rect x="140" y="100" width="220" height="55" rx="12" fill="#1a1a2e" stroke="#34d399" stroke-width="2"/>
<text x="250" y="123" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="12" font-weight="700">Gateway (FastAPI)</text>
<text x="250" y="140" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">Sesiones | Rate-limit | Routing</text>

<!-- Flecha al agente -->
<line x1="250" y1="155" x2="450" y2="200" stroke="#34d399" stroke-width="1.5"/>

<!-- Agente Orquestador -->
<rect x="310" y="195" width="280" height="75" rx="14" fill="#1a1a2e" stroke="#facc15" stroke-width="2"/>
<text x="450" y="222" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="13" font-weight="800">Agente Odin</text>
<text x="450" y="240" text-anchor="middle" fill="#facc15" font-family="Inter" font-size="10" font-weight="600">Gemini 2.5 Pro + Google ADK</text>
<text x="450" y="256" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">Orquesta 3 MCP Servers</text>

<!-- MCP 1: Anticorrupcion -->
<rect x="80" y="320" width="200" height="55" rx="10" fill="#1a1a2e" stroke="#f87171" stroke-width="1.5"/>
<text x="180" y="343" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">MCP Anticorrupcion</text>
<text x="180" y="360" text-anchor="middle" fill="#f87171" font-family="Inter" font-size="9" font-weight="600">7 tools | Alertas + Scoring</text>
<line x1="350" y1="270" x2="220" y2="320" stroke="#f87171" stroke-width="1" stroke-dasharray="4"/>

<!-- MCP 2: Gasto -->
<rect x="350" y="320" width="200" height="55" rx="10" fill="#1a1a2e" stroke="#22d3ee" stroke-width="1.5"/>
<text x="450" y="343" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">MCP Gasto Publico</text>
<text x="450" y="360" text-anchor="middle" fill="#22d3ee" font-family="Inter" font-size="9" font-weight="600">7 tools | Presupuesto + CDPs</text>
<line x1="450" y1="270" x2="450" y2="320" stroke="#22d3ee" stroke-width="1" stroke-dasharray="4"/>

<!-- MCP 3: Mercado -->
<rect x="620" y="320" width="200" height="55" rx="10" fill="#1a1a2e" stroke="#34d399" stroke-width="1.5"/>
<text x="720" y="343" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">MCP Mercado</text>
<text x="720" y="360" text-anchor="middle" fill="#34d399" font-family="Inter" font-size="9" font-weight="600">6 tools | Oportunidades</text>
<line x1="550" y1="270" x2="680" y2="320" stroke="#34d399" stroke-width="1" stroke-dasharray="4"/>

<!-- BigQuery -->
<rect x="270" y="420" width="220" height="45" rx="10" fill="#1a1a2e" stroke="#818cf8" stroke-width="2"/>
<text x="380" y="440" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="700">BigQuery (131M+ rows)</text>
<text x="380" y="455" text-anchor="middle" fill="#71717a" font-family="Inter" font-size="9">11 tablas SECOP II</text>
<line x1="180" y1="375" x2="320" y2="420" stroke="#818cf8" stroke-width="1" stroke-dasharray="3"/>
<line x1="450" y1="375" x2="380" y2="420" stroke="#818cf8" stroke-width="1" stroke-dasharray="3"/>
<line x1="720" y1="375" x2="440" y2="420" stroke="#818cf8" stroke-width="1" stroke-dasharray="3"/>

<!-- Chart Engine -->
<rect x="620" y="110" width="200" height="50" rx="10" fill="#1a1a2e" stroke="#fb923c" stroke-width="1.5"/>
<text x="720" y="132" text-anchor="middle" fill="#e4e4e7" font-family="Inter" font-size="11" font-weight="600">Chart Engine</text>
<text x="720" y="148" text-anchor="middle" fill="#fb923c" font-family="Inter" font-size="9">matplotlib | networkx | PNG</text>
<line x1="590" y1="230" x2="660" y2="155" stroke="#fb923c" stroke-width="1" stroke-dasharray="4"/>

</svg>
</div>
</div>

<!-- MCP 1 -->
<div class="sec">
<div class="sec-l" style="color:var(--r)">MCP Server 1</div>
<div class="sec-t">Observatorio Anticorrupcion</div>
<div class="sec-d">7 herramientas especializadas en deteccion de riesgos. Archivo: <code>agent/mcp_anticorrupcion.py</code></div>

<table><thead><tr><th>Tool</th><th>Descripcion</th><th>Tablas y Campos</th></tr></thead><tbody>
<tr><td><b>buscar_proveedor_monopolista</b></td><td>Proveedores con >80% de contratos en una entidad</td><td>contratos(nombre_entidad, documento_proveedor, valor_del_contrato)<br>proponentes(nit_proveedor, entidad_compradora)</td></tr>
<tr><td><b>detectar_fraccionamiento</b></td><td>Minimas cuantias que sumadas superan umbral de licitacion</td><td>contratos(modalidad_de_contratacion, valor_del_contrato, documento_proveedor, nombre_entidad, fecha_de_firma)</td></tr>
<tr><td><b>licitacion_sin_competencia</b></td><td>Procesos competitivos con 1 solo proponente</td><td>procesos(id_del_proceso, modalidad, proveedores_unicos_con_respuesta)<br>proponentes(id_procedimiento, nit_proveedor)</td></tr>
<tr><td><b>proveedor_sancionado_activo</b></td><td>Sancionados con contratos nuevos</td><td>multas(documento_proveedor, tipo_sanci_n, fecha_sanci_n)<br>contratos(documento_proveedor, fecha_de_firma)</td></tr>
<tr><td><b>red_proveedores</b></td><td>Grafo de relaciones entre consorcios</td><td>grupos_proveedores(nit_participante, nit_grupo, nombre_grupo, es_lider)<br>contratos(es_grupo, documento_proveedor)</td></tr>
<tr><td><b>scoring_riesgo_entidad</b></td><td>Score 0-100 combinando todas las alertas</td><td>Cruza las 6 tools anteriores por entidad</td></tr>
<tr><td><b>sobrefacturacion</b></td><td>Facturas que superan valor contrato + adiciones</td><td>facturas(id_contrato, valor_total)<br>contratos(id_contrato, valor_del_contrato)<br>adiciones(id_contrato, tipo)</td></tr>
</tbody></table>
</div>

<!-- MCP 2 -->
<div class="sec">
<div class="sec-l" style="color:var(--cy)">MCP Server 2</div>
<div class="sec-t">Seguimiento del Gasto Publico</div>
<div class="sec-d">7 herramientas para monitoreo presupuestal. Archivo: <code>agent/mcp_gasto.py</code></div>

<table><thead><tr><th>Tool</th><th>Descripcion</th><th>Tablas y Campos</th></tr></thead><tbody>
<tr><td><b>ejecucion_presupuestal</b></td><td>% ejecucion por entidad, depto o periodo</td><td>contratos(nombre_entidad, valor_del_contrato, valor_pagado, departamento)<br>compromisos(id_contrato, valor_item, balance_compromiso)</td></tr>
<tr><td><b>comparar_entidades</b></td><td>Benchmarking entre entidades similares</td><td>contratos(nombre_entidad, sector, valor_del_contrato, modalidad_de_contratacion)</td></tr>
<tr><td><b>cdps_sin_contrato</b></td><td>CDPs que nunca se materializaron</td><td>solicitudes_cdps(id_contrato, entidad, saldo_total_a_comprometer, estado_del_contrato)</td></tr>
<tr><td><b>mora_pagos_entidad</b></td><td>Dias promedio de pago por entidad</td><td>facturas(id_contrato, fecha_factura, pago_confirmado, fecha_estiamda_de_pago)<br>contratos(id_contrato, nombre_entidad)</td></tr>
<tr><td><b>gasto_por_modalidad</b></td><td>Distribucion del gasto por tipo de contratacion</td><td>contratos(modalidad_de_contratacion, valor_del_contrato, nombre_entidad)</td></tr>
<tr><td><b>concentracion_directa</b></td><td>Entidades con >70% contratacion directa</td><td>contratos(nombre_entidad, modalidad_de_contratacion, valor_del_contrato)</td></tr>
<tr><td><b>contratos_vencidos</b></td><td>Contratos vencidos sin liquidar (>180 dias)</td><td>contratos(id_contrato, fecha_de_fin_del_contrato, liquidacion, estado_contrato, valor_pendiente_de_ejecucion)</td></tr>
</tbody></table>
</div>

<!-- MCP 3 -->
<div class="sec">
<div class="sec-l" style="color:var(--g)">MCP Server 3</div>
<div class="sec-t">Inteligencia de Mercado</div>
<div class="sec-d">6 herramientas para proveedores y analistas. Archivo: <code>agent/mcp_mercado.py</code></div>

<table><thead><tr><th>Tool</th><th>Descripcion</th><th>Tablas y Campos</th></tr></thead><tbody>
<tr><td><b>oportunidades_sector</b></td><td>Procesos activos por categoria UNSPSC</td><td>procesos(id_del_proceso, estado_del_procedimiento, codigo_principal_de_categoria, precio_base)</td></tr>
<tr><td><b>perfil_proveedor</b></td><td>Historial completo de un proveedor</td><td>contratos(documento_proveedor, valor_del_contrato, fecha_de_firma)<br>proponentes(nit_proveedor)<br>multas(documento_proveedor)</td></tr>
<tr><td><b>competencia_sector</b></td><td>Top proveedores por sector</td><td>contratos(sector, documento_proveedor, proveedor_adjudicado, valor_del_contrato)</td></tr>
<tr><td><b>tendencia_contratacion</b></td><td>Evolucion temporal del gasto</td><td>contratos(fecha_de_firma, valor_del_contrato, sector, departamento)</td></tr>
<tr><td><b>requisitos_habituales</b></td><td>Que piden las entidades por tipo de contrato</td><td>procesos(tipo_de_contrato, modalidad_de_contratacion, duracion, precio_base)</td></tr>
<tr><td><b>mapa_territorial</b></td><td>Gasto por departamento/municipio</td><td>contratos(departamento, ciudad, valor_del_contrato, nombre_entidad)</td></tr>
</tbody></table>
</div>

<!-- ESTRUCTURA -->
<div class="sec">
<div class="sec-l">Estructura del proyecto</div>
<div class="sec-t">Archivos y directorios</div>
<pre>
odin-v2/
+-- ingestion/                     <span style="color:var(--g)"># Ya existe</span>
|   +-- initial_load.py
|   +-- initial_load_generic.py
|   +-- daily_sync.py
|
+-- agent/                         <span style="color:var(--o)"># Nuevo</span>
|   +-- odin_agent.py              <span style="color:var(--m)"># Agente orquestador ADK</span>
|   +-- mcp_anticorrupcion.py      <span style="color:var(--r)"># MCP 1: alertas</span>
|   +-- mcp_gasto.py               <span style="color:var(--cy)"># MCP 2: presupuesto</span>
|   +-- mcp_mercado.py             <span style="color:var(--g)"># MCP 3: mercado</span>
|   +-- charts.py                  <span style="color:var(--o)"># Generador de graficos PNG</span>
|   +-- bq_client.py               <span style="color:var(--m)"># Cliente BigQuery compartido</span>
|   +-- config.py                  <span style="color:var(--m)"># Configuracion centralizada</span>
|
+-- bot/                           <span style="color:var(--o)"># Nuevo</span>
|   +-- telegram_bot.py            <span style="color:var(--a)"># Gateway Telegram (MVP)</span>
|   +-- whatsapp_webhook.py        <span style="color:var(--m)"># Gateway WhatsApp (Fase 2)</span>
|
+-- deploy/                        <span style="color:var(--o)"># Nuevo</span>
|   +-- Dockerfile
|   +-- cloudbuild.yaml
|   +-- scheduler.yaml
+-- requirements.txt
</pre>
</div>

<!-- STACK -->
<div class="sec">
<div class="sec-l">Stack tecnologico</div>
<div class="sec-t">Dependencias principales</div>
<div class="grid2">
<div class="card">
<h3><span class="tag tag-y">CORE</span> Agente</h3>
<table><tbody>
<tr><td>LLM</td><td><b>Gemini 2.5 Pro</b> (via Vertex AI)</td></tr>
<tr><td>Framework</td><td><b>Google ADK</b> (Agent Dev Kit)</td></tr>
<tr><td>Protocolo</td><td><b>MCP</b> (Model Context Protocol)</td></tr>
<tr><td>Runtime</td><td>Python 3.11+</td></tr>
</tbody></table>
</div>
<div class="card">
<h3><span class="tag tag-cy">DATA</span> Backend</h3>
<table><tbody>
<tr><td>Data Warehouse</td><td><b>BigQuery</b> (GCP)</td></tr>
<tr><td>Charts</td><td><b>matplotlib</b> + <b>plotly</b></td></tr>
<tr><td>Grafos</td><td><b>NetworkX</b></td></tr>
<tr><td>API</td><td><b>FastAPI</b></td></tr>
</tbody></table>
</div>
<div class="card">
<h3><span class="tag tag-g">CANAL</span> Comunicacion</h3>
<table><tbody>
<tr><td>MVP</td><td><b>Telegram Bot API</b></td></tr>
<tr><td>Fase 2</td><td>WhatsApp Business API</td></tr>
<tr><td>Sesiones</td><td>Redis (Cloud Memorystore)</td></tr>
</tbody></table>
</div>
<div class="card">
<h3><span class="tag tag-o">DEPLOY</span> Infra</h3>
<table><tbody>
<tr><td>Agente</td><td><b>Cloud Run</b> (servicio)</td></tr>
<tr><td>Sync</td><td>Cloud Run Jobs + Scheduler</td></tr>
<tr><td>CI/CD</td><td>Cloud Build</td></tr>
<tr><td>Costo est.</td><td>~$15-25 USD/mes</td></tr>
</tbody></table>
</div>
</div>
</div>

<!-- PREGUNTAS -->
<div class="sec">
<div class="sec-l" style="color:var(--y)">Decisiones pendientes</div>
<div class="sec-t">Necesito tu input para empezar</div>

<div class="q-card">
<b>1. Google ADK vs LangChain</b>
<p>Recomiendo <b>Google ADK</b> por integracion nativa con Gemini y MCP. LangChain es mas maduro pero agrega complejidad innecesaria aqui.</p>
</div>

<div class="q-card">
<b>2. Telegram como MVP</b>
<p>Propongo empezar con <b>Telegram</b> (gratis, sin aprobacion de Meta, API simple). Tienes ya un bot creado con @BotFather? Si no, lo creamos en 2 minutos.</p>
</div>

<div class="q-card">
<b>3. API Key de Gemini</b>
<p>Tienes API key de Gemini configurada en GCP? Podemos usar <b>Vertex AI</b> (ya tienes proyecto odin-v2-495523) o una API key directa de Google AI Studio.</p>
</div>
</div>

<div class="ft">
<b>Odin v2</b> | Arquitectura de Agentes | 8 mayo 2026
</div>

</div></body></html>"""

with open("docs/arquitectura_agentes.html", "w", encoding="utf-8") as f:
    f.write(html)
print("OK: docs/arquitectura_agentes.html")
