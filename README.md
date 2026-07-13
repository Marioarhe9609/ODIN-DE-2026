# ⚖️ ODIN v2 — Ecosistema de Inteligencia Analítica Preventiva

> **Plataforma de análisis predictivo y prevención en contratación pública colombiana.**  
> *Alineado con el Reto de Seguridad Ciudadana y Justicia 2026.*

---

## 📌 Descripción de la Solución
**ODIN v2** es un sistema de inteligencia preventiva orientado a la identificación de patrones asociados a posibles riesgos de delitos en la contratación estatal (corrupción, colusión, fraude y afectación al patrimonio público). 

La solución procesa más de **149 millones de registros**, integra **13 fuentes oficiales** de Colombia Compra Eficiente (SECOP II) y articula **46 herramientas analíticas**, **25 alertas tempranas** y **cinco modelos analíticos**. Esto permite reconocer comportamientos recurrentes, anomalías, relaciones entre actores y dinámicas contractuales que constituyen señales tempranas de posibles hechos irregulares, apoyando la labor de entidades de justicia y control, veedurías ciudadanas y la ciudadanía en general.

---

## 🎯 Alineación con la Categoría: Seguridad Ciudadana y Justicia
La contratación pública genera información de alto valor para la seguridad económica y la administración de justicia. El reto de ODIN v2 es transformar este universo de datos abiertos en señales predictivas y explicables para anticipar escenarios de riesgo y focalizar la revisión humana de las autoridades.

| Criterio de la Categoría | Respuesta de ODIN v2 |
|---|---|
| **Seguimiento de gestión mediante reportes claros** | Tableros, gráficos, perfiles de proveedores, entidades, tendencias y redes explicables. |
| **Mecanismos de prevención y auditoría ciudadana** | Acceso a consultas, alertas, trazabilidad de fuentes y diagnósticos reproducibles para control social. |
| **Integración de datos abiertos para la confianza** | 13 conjuntos de datos oficiales de Colombia Compra Eficiente unificados en una base analítica. |
| **Indicadores de transparencia y buenas prácticas** | Semáforo de transparencia, scoring de riesgo (0-100), alertas por concentración y anomalías. |

---

## 🧠 Modelos Analíticos Implementados
ODIN v2 aplica modelos híbridos de analítica predictiva, grafos de red, reglas de negocio e IA generativa:

1. **🕸️ Detección de Colusión y Redes de Posible Criminalidad**: Mapea esquemas de *bid rigging* (manipulación de licitaciones) identificando representantes legales que participan con múltiples empresas en el mismo proceso y redes de representación compartida.
2. **🚦 Semáforo de Transparencia Procesal**: Cruza compromisos presupuestales, monopolios históricos y alertas tempranas para calificar procesos de licitación antes de su adjudicación.
3. **📊 Scoring de Riesgo de Corrupción (0-100)**: Pondera 20+ categorías de alerta por severidad para priorizar investigaciones de control fiscal o disciplinario.
4. **🔮 Pronóstico de Demanda y Detección de Anomalías**: Regresión lineal in-BigQuery que calcula desviaciones significativas respecto a la tendencia de gasto histórica por sector/UNSPSC.
5. **🤖 Análisis de Pliegos con IA Generativa**: Utiliza Gemini 2.5 Flash para extraer requisitos técnicos, financieros y de experiencia mínima de pliegos PDF para detectar "pliegos sastre" o restrictivos.

---

## 📈 Fuentes de Datos Integradas (149M+ Registros)
- Contratos Electrónicos (SECOP II)
- Procesos de Contratación
- Proponentes por Proceso
- Modificaciones de Contratos
- Adiciones Presupuestales
- Multas y Sanciones
- Suspensiones de Contratos
- Compromisos Presupuestales
- Solicitudes CDPs
- Plan Anual de Adquisiciones (PAA)
- Grupos de Proveedores
- Facturas
- Tienda Virtual Consolidado

---

## 🛠️ Stack Tecnológico
- **Data Warehouse**: Google BigQuery (Particionado por fecha de firma, clusterizado por entidad/departamento).
- **Core Engine**: Python 3.12 + Google ADK (Agent Development Kit).
- **IA/LLM**: Gemini 2.5 Pro (Agente cognitivo) & Gemini 2.5 Flash (Extracción de pliegos).
- **User Interface**: Telegram Bot en Cloud Run (Soporta streaming de respuestas, gráficos dinámicos con matplotlib y reportes automatizados en PDF/Excel).

---

## ⚙️ Estructura del Proyecto
```
Odin-v2/
├── agent/                          # Agente ADK + herramientas cognitivas
│   ├── tools_anticorrupcion.py     # 17 herramientas anticorrupción y colusión
│   ├── tools_gasto.py              # 9 herramientas de control fiscal de gasto
│   ├── tools_mercado.py            # 13 herramientas de mercado y competencia
│   └── tools_graficos.py           # 6 herramientas de visualización de redes y charts
├── bot/                            # Gateway del Bot de Telegram (Cloud Run)
├── ingestion/                      # Pipeline de ingesta masiva e incremental (SODA API)
├── scripts/                        # Scripts de configuración y auditoría
├── docs/                           # Documentación de arquitectura e implementación
├── Dockerfile                      # Despliegue en contenedor
└── requirements.txt                # Dependencias del proyecto
```

---

## ⚖️ Propuesta de Valor y Descargo de Responsabilidad
ODIN v2 **no declara que exista un delito o corrupción de forma automática**. Su función es identificar patrones de riesgo, anomalías y combinaciones de factores atípicos que requieran ser revisados por personas, veedurías ciudadanas o autoridades competentes. Sus resultados son señales explicables diseñadas para priorizar el análisis y la toma de decisiones preventivas.
