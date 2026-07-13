# Arquitectura de Agentes Odin v2

## Contexto

Basado en la propuesta (`propuesta_odin.html`), Odin tiene 3 líneas de producto:
1. **Observatorio Anticorrupción** — 25 alertas automatizadas
2. **Seguimiento del Gasto Público** — ejecución presupuestal, CDPs, facturas
3. **Inteligencia de Mercado** — oportunidades, competencia, proveedores

El agente debe ser conversacional (Telegram MVP → WhatsApp), generar gráficos y cruzar 11 tablas con 131M+ registros en BigQuery.

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────┐
│                    CANALES                           │
│   Telegram Bot  ←→  WhatsApp API  ←→  Web (futuro)  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              GATEWAY (FastAPI)                       │
│  - Recibe mensajes de cualquier canal                │
│  - Gestiona sesiones y rate-limiting                 │
│  - Enruta al agente orquestador                      │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          AGENTE ORQUESTADOR (Gemini 2.5 Pro)         │
│  Google ADK Agent con 3 MCP Servers                  │
│  - Entiende la pregunta del usuario                  │
│  - Decide qué herramientas usar                      │
│  - Combina resultados y responde                     │
└───┬──────────────────┬──────────────────┬───────────┘
    │                  │                  │
┌───▼────┐       ┌─────▼─────┐      ┌────▼────┐
│ MCP 1  │       │  MCP 2    │      │ MCP 3   │
│Anticorr│       │  Gasto    │      │ Mercado │
└───┬────┘       └─────┬─────┘      └────┬────┘
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
              ┌────────▼────────┐
              │    BigQuery     │
              │  11 tablas      │
              │  131M+ registros│
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Chart Engine   │
              │  (matplotlib)   │
              │  Genera PNGs    │
              └─────────────────┘
```

## Proposed Changes

### Componente 1: MCP Servers (Model Context Protocol)

Cada MCP Server expone herramientas especializadas por dominio. Esto permite que el agente orquestador use solo las herramientas relevantes a cada pregunta.

---

#### [NEW] `agent/mcp_anticorrupcion.py`

MCP Server para el Observatorio Anticorrupción. Expone las siguientes tools:

| Tool | Descripción | Tablas |
|---|---|---|
| `buscar_proveedor_monopolista` | Proveedores con >80% contratos de una entidad | contratos, proponentes |
| `detectar_fraccionamiento` | Mínimas cuantías que suman más que licitación | contratos |
| `licitacion_sin_competencia` | Procesos con 1 solo proponente | procesos, proponentes |
| `proveedor_sancionado_activo` | Proveedores sancionados con contratos nuevos | multas, contratos |
| `red_proveedores` | Grafo de relaciones entre proveedores y consorcios | grupos_proveedores, contratos |
| `scoring_riesgo_entidad` | Score de riesgo por entidad (combina varias alertas) | todas |
| `sobrefacturacion` | Facturas que superan valor del contrato + adiciones | facturas, contratos, adiciones |

---

#### [NEW] `agent/mcp_gasto.py`

MCP Server para Seguimiento del Gasto Público.

| Tool | Descripción | Tablas |
|---|---|---|
| `ejecucion_presupuestal` | % ejecución por entidad/departamento/periodo | contratos, compromisos |
| `comparar_entidades` | Benchmarking entre entidades similares | contratos |
| `cdps_sin_contrato` | CDPs que nunca se materializaron en contrato | solicitudes_cdps |
| `mora_pagos_entidad` | Días promedio de pago por entidad | facturas, contratos |
| `gasto_por_modalidad` | Distribución del gasto por modalidad | contratos |
| `concentracion_directa` | Entidades con >70% contratación directa | contratos |
| `contratos_vencidos` | Contratos vencidos sin liquidar | contratos |

---

#### [NEW] `agent/mcp_mercado.py`

MCP Server para Inteligencia de Mercado.

| Tool | Descripción | Tablas |
|---|---|---|
| `oportunidades_sector` | Procesos activos por categoría UNSPSC | procesos |
| `perfil_proveedor` | Historial completo de un proveedor | contratos, proponentes, multas |
| `competencia_sector` | Top proveedores por sector/categoría | contratos |
| `tendencia_contratacion` | Evolución temporal del gasto por categoría | contratos |
| `requisitos_habituales` | Qué piden las entidades para un tipo de contrato | procesos |
| `mapa_territorial` | Gasto por departamento/municipio | contratos |

---

### Componente 2: Agente Orquestador

#### [NEW] `agent/odin_agent.py`

Agente principal usando Google ADK (Agent Development Kit):

```python
from google.adk import Agent
from google.adk.tools import McpToolset

agent = Agent(
    model="gemini-2.5-pro",
    name="Odin",
    instructions="""Eres Odin, un agente experto en contratación 
    pública colombiana. Tienes acceso a 131M+ registros de SECOP II.
    Responde en español. Cuando generes datos tabulares, 
    también genera un gráfico si es relevante.""",
    tools=[
        McpToolset(server="mcp_anticorrupcion"),
        McpToolset(server="mcp_gasto"),
        McpToolset(server="mcp_mercado"),
    ]
)
```

---

### Componente 3: Chart Engine

#### [NEW] `agent/charts.py`

Genera gráficos PNG que se envían como imágenes por Telegram/WhatsApp.

Tipos soportados:
- **Barras/Líneas**: matplotlib para tendencias y comparativas
- **Grafos de red**: NetworkX para relaciones proveedor-entidad
- **Mapas de calor**: Para concentración territorial

---

### Componente 4: Gateway Telegram

#### [NEW] `agent/telegram_bot.py`

Bot de Telegram usando `python-telegram-bot`:
- Recibe mensajes del usuario
- Los pasa al agente orquestador
- Devuelve texto + imágenes (gráficos)
- Rate limiting por usuario (100 consultas/mes plan básico)

---

### Estructura de archivos propuesta

```
odin-v2/
├── ingestion/                    # ✅ Ya existe
│   ├── initial_load.py
│   ├── initial_load_procesos.py
│   ├── initial_load_generic.py
│   └── daily_sync.py
├── agent/                        # 🆕 Nuevo
│   ├── __init__.py
│   ├── odin_agent.py             # Agente orquestador (ADK)
│   ├── mcp_anticorrupcion.py     # MCP Server: alertas
│   ├── mcp_gasto.py              # MCP Server: presupuesto
│   ├── mcp_mercado.py            # MCP Server: mercado
│   ├── charts.py                 # Generador de gráficos
│   ├── bq_client.py              # Cliente BigQuery compartido
│   └── config.py                 # Configuración centralizada
├── bot/                          # 🆕 Nuevo
│   ├── telegram_bot.py           # Gateway Telegram
│   └── whatsapp_webhook.py       # Gateway WhatsApp (futuro)
├── deploy/                       # 🆕 Nuevo
│   ├── Dockerfile
│   ├── cloudbuild.yaml
│   └── scheduler.yaml
└── requirements.txt
```

## Open Questions

> [!IMPORTANT]
> **1. Google ADK vs LangChain/LangGraph:** ¿Prefieres usar Google ADK (más nativo con Gemini, más nuevo) o LangChain (más maduro, más documentación)? Mi recomendación es **Google ADK** por integración directa con Gemini 2.5 Pro y MCP nativo.

> [!IMPORTANT]  
> **2. Telegram primero:** El MVP será en Telegram (gratis, sin aprobación de Meta). ¿Tienes ya un bot de Telegram creado o lo creamos desde cero con @BotFather?

> [!IMPORTANT]
> **3. Gemini API Key:** ¿Ya tienes una API key de Gemini configurada en el proyecto GCP, o usamos la de Vertex AI?

## Verification Plan

### Automated Tests
- Test unitario por cada tool de MCP (query mock)
- Test de integración: pregunta → agente → BigQuery → respuesta
- Test de gráficos: verificar que se genera PNG válido

### Manual Verification
- Enviar preguntas reales al bot de Telegram
- Verificar que las respuestas cruzan datos correctamente
- Validar gráficos generados
