"""Odin v2 - Telegram Bot Gateway for Cloud Run.
Unified aiohttp server for Webhook and Polling modes.
"""
import os
os.environ["OTEL_SDK_DISABLED"] = "TRUE"
import sys
# Add parent to path first to allow absolute imports of agent module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import tempfile
import re
import base64
import json
import urllib.parse
import aiohttp
from aiohttp import web
from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ADK imports
from google.adk.runners import Runner
from agent.bq_session_service import BigQuerySessionService
from google.genai import types as genai_types
from agent import odin_agent
from agent.bq_client import client, PROJECT, DATASET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("odin_bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

PORT = int(os.getenv("PORT", "8080"))


# ── ADK Runner setup ──────────────────────────────────────────────────────
session_service = BigQuerySessionService()
runner = Runner(agent=odin_agent, app_name="odin_bot", session_service=session_service)

async def get_agent_response(user_id: str, message: str) -> str:
    """Send a message to the ADK agent and return the response."""
    session = await session_service.get_session(
        app_name="odin_bot", user_id=user_id, session_id=user_id
    )
    if not session:
        session = await session_service.create_session(
            app_name="odin_bot", user_id=user_id, session_id=user_id
        )
    
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=message)]
    )
    
    final_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=user_id,
        new_message=user_content
    ):
        logger.info(f"Event received: {type(event).__name__}")
        if event.is_final_response():
            if event.content and event.content.parts:
                logger.info(f"Final response parts: {len(event.content.parts)}")
                for part in event.content.parts:
                    if part.text:
                        final_response += part.text
                    else:
                        logger.warning(f"Part has no text. Keys: {dir(part)}")
            else:
                logger.warning("Final response event received but content or parts is None")
    
    if not final_response:
        logger.error(f"Agent returned empty response for user {user_id}")
    return final_response or "No pude procesar tu consulta. Intenta de nuevo."


# ── PDF Generation (imported from module) ─────────────────────────────────
from bot.pdf_generator import generate_pdf


# ── SECOP Document Download ───────────────────────────────────────────────
async def download_secop_document(doc_id, filename):
    """Try to download a SECOP II document. Returns file path or None."""
    urls = [
        f"https://community.secop.gov.co/Public/Common/AjaxRequestHandler/handler.ashx?MethodName=GetFileByDocumentId&DocumentId={doc_id}",
        f"https://community.secop.gov.co/Public/Common/Actions/GetFileContentAction?documentId={doc_id}",
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if len(content) > 100:
                            path = os.path.join(tempfile.gettempdir(), filename)
                            with open(path, "wb") as f:
                                f.write(content)
                            return path
        except Exception as e:
            logger.warning(f"Download attempt failed for {doc_id}: {e}")
    return None


# ── Natural-language PDF/Excel detection ──────────────────────────────────
def wants_pdf(msg):
    """Return True if the user's message asks for a PDF."""
    low = msg.lower()
    triggers = [
        "pdf", "en pdf", "como pdf", "formato pdf",
        "genera informe", "genera un informe", "genera el informe",
        "generar informe", "dame informe", "dame el informe",
        "dame un informe", "exporta", "exportar",
        "descarga informe", "descargar informe",
    ]
    return any(t in low for t in triggers)


def wants_excel(msg):
    """Return True if the user's message asks for an Excel spreadsheet."""
    low = msg.lower()
    triggers = [
        "excel", "xlsx", "descargar excel", "descarga excel", 
        "exportar excel", "exporta excel", "tabla excel", "archivo excel"
    ]
    return any(t in low for t in triggers)


# ── Telegram handlers ─────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Reset session on /start
    try:
        await session_service.delete_session(app_name="odin_bot", user_id=user_id, session_id=user_id)
        logger.info(f"Session reset for user {user_id} via /start")
    except Exception as e:
        logger.error(f"Error resetting session for {user_id}: {e}")

    welcome = (
        "👁️ Hola! Soy *Odin*, tu agente de inteligencia en contratación pública colombiana.\n\n"
        "Tengo acceso a *149M+ registros* de SECOP II.\n\n"
        "🔴 *Anticorrupción* - Monopolios, fraccionamiento, sobrecostos\n"
        "📊 *Gasto Público* - Ejecución presupuestal, CDPs, pagos\n"
        "📈 *Mercado* - Perfiles de proveedores, competencia, proyecciones\n"
        "📄 *Documentos* - Archivos de contratos SECOP\n\n"
        "Usa /reset para iniciar una nueva conversación limpia.\n\n"
        "*Para generar PDF*, solo agrega 'pdf' o 'informe' a tu solicitud:\n"
        '_"Dame un informe en pdf del diagnostico de INVIAS"_\n\n'
        "/doc `ID` - Descarga documento SECOP por ID\n"
        "/help - Ver más ejemplos\n"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    user_id = str(update.effective_user.id)
    try:
        await session_service.delete_session(app_name="odin_bot", user_id=user_id, session_id=user_id)
        logger.info(f"Session reset for user {user_id} via /reset")
        await update.message.reply_text("🗑️ Historial de conversación borrado. Puedes empezar de cero.")
    except Exception as e:
        logger.error(f"Error resetting session for {user_id}: {e}")
        await update.message.reply_text("⚠️ No pude borrar el historial. Intenta de nuevo.")


GRAPH_CACHE = {}
MEMORY_CACHE = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_msg = update.message.text
    logger.info(f"User {user_id}: {user_msg[:80]}")

    # Normalize Spanish characters and remove punctuation
    clean_msg = user_msg.lower()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "n", "¿": "", "?": "", "!": "",
        "¡": "", ".": "", ",": ""
    }
    for k, v in replacements.items():
        clean_msg = clean_msg.replace(k, v)
    clean_msg = clean_msg.strip()

    # Automatic Profile NIT Extraction
    nit_match = re.search(r'\b(\d{9})\b', user_msg)
    if nit_match:
        nit = nit_match.group(1)
        session = await session_service.get_session(app_name="odin_bot", user_id=user_id, session_id=user_id)
        if session:
            session.state["nit"] = nit
            await session_service._save_session(session)
            logger.info(f"Saved profile NIT {nit} to session state for user {user_id}")
    elif "espacios y redes" in clean_msg:
        session = await session_service.get_session(app_name="odin_bot", user_id=user_id, session_id=user_id)
        if session:
            session.state["nit"] = "830144531"
            await session_service._save_session(session)
            logger.info(f"Saved default profile 'Espacios y Redes' (NIT 830144531) to session state for user {user_id}")

    greetings = [
        "hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "buen dia", 
        "oe", "quiubo", "como estas", "como esta", "como te va", "como vas", "como va",
        "como va todo", "que tal", "que mas", "hola odin", "bueno", "buenas", "que tal todo",
        "como estas odin", "que mas odin"
    ]
    
    is_greeting_msg = (clean_msg in greetings) or (
        len(clean_msg) < 35 and any(kw in clean_msg for kw in [
            "hola", "como estas", "como vas", "que tal", "quiubo", "buenos dias", "saludos", "como va"
        ])
    )

    if is_greeting_msg:
        greeting_resp = (
            "¡Hola! Qué gusto saludarte. Excelente día.\n\n"
            "Soy **Odin**, tu agente de inteligencia en contratación pública colombiana. "
            "Tengo acceso a más de 149M+ de registros de SECOP II en tiempo real.\n\n"
            "¿En qué te puedo colaborar hoy? Puedes consultarme por:\n"
            "• Recomendación de oportunidades (ej: *'Soy espacios y redes, dame procesos recomendados'*)\n"
            "• Historial de contratistas o entidades específicas\n"
            "• Diagnósticos de riesgo y alertas de colusión/corrupción\n"
            "• Predicciones de demanda (ej: *'Predice la demanda de software para 2026'*)"
        )
        await update.message.reply_text(greeting_resp, parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")

    send_pdf = wants_pdf(user_msg)
    send_excel = wants_excel(user_msg)

    # Strip PDF/Excel-related words so the agent doesn't get confused
    agent_msg = user_msg
    if send_pdf:
        for word in ["en pdf", "como pdf", "formato pdf", "pdf",
                      "genera un informe de", "genera informe de",
                      "genera el informe de", "dame un informe de",
                      "dame el informe de", "dame informe de",
                      "genera un informe", "genera informe",
                      "exporta", "exportar"]:
            agent_msg = re.sub(re.escape(word), "", agent_msg, flags=re.IGNORECASE)

    if send_excel:
        for word in ["descargar excel", "descarga excel", "exportar excel", "exporta excel",
                      "tabla excel", "archivo excel", "en excel", "como excel", "formato excel",
                      "excel", "xlsx"]:
            agent_msg = re.sub(re.escape(word), "", agent_msg, flags=re.IGNORECASE)

    agent_msg = re.sub(r'\s+', ' ', agent_msg).strip()
    if len(agent_msg) < 5:
        agent_msg = user_msg  # Fallback

    if send_pdf:
        agent_msg += "\n[SYSTEM: El usuario ha solicitado un PDF/informe. Si los resultados de tu consulta contienen datos numéricos (como montos, presupuestos, adiciones, conteos), DEBES generar de forma obligatoria al menos un gráfico adecuado usando tus herramientas (como generar_grafico_barras, generar_grafico_pastel, generar_grafico_dona, etc.) e incluir el marcador [CHART:id] en tu respuesta final.]"

    if send_excel:
        agent_msg += "\n[SYSTEM: El usuario ha solicitado descargar en Excel la última búsqueda. DEBES volver a ejecutar EXACTAMENTE la misma herramienta con los mismos parámetros que usaste en tu respuesta anterior para que el sistema regenere los datos y cree el archivo Excel. NO cambies el enfoque ni realices un análisis distinto al anterior a menos que el usuario lo pida explícitamente.]"

    from agent.bq_client import generated_excels_var
    excels_list = []
    token = generated_excels_var.set(excels_list)

    try:
        import time
        now = time.time()
        if now - MEMORY_CACHE.get("last_fetched", 0) > 60:
            from google.cloud import bigquery
            from agent.bq_client import PROJECT, DATASET
            client = bigquery.Client(project=PROJECT)
            try:
                mem_rows = client.query(f"SELECT regla FROM `{PROJECT}.{DATASET}.memoria_odin`").result()
                MEMORY_CACHE["rules"] = [r.regla for r in mem_rows]
                MEMORY_CACHE["last_fetched"] = now
            except Exception as eq:
                logger.warning(f"Memoria odin no existe aun o fallo: {eq}")
                
        if MEMORY_CACHE.get("rules"):
            reglas_str = "\n- ".join(MEMORY_CACHE["rules"])
            agent_msg += f"\n\n[INSTRUCCIÓN INTERNA (MEMORIA DE LARGO PLAZO):\nTen en cuenta las siguientes reglas de negocio que el usuario te ha enseñado previamente:\n- {reglas_str}\n\nAplica estrictamente estas reglas al responder o generar consultas.]"
    except Exception as e:
        logger.warning(f"Error fetching memory rules: {e}")

    try:
        response = await get_agent_response(user_id, agent_msg)

        # Extract chart markers from response
        chart_markers = re.findall(r'\[CHART:(\w+)\]', response)
        chart_paths = {}
        if chart_markers:
            from agent.tools_graficos import get_chart_path
            for cid in chart_markers:
                cpath = get_chart_path(cid)
                if os.path.exists(cpath):
                    chart_paths[cid] = cpath

        # Clean markers from text for Telegram display
        display_text = re.sub(r'\[CHART:\w+\][^\n]*', '', response).strip()
        display_text = re.sub(r'\[EXCEL:[^\]]+\][^\n]*', '', display_text).strip()
        display_text = re.sub(r'\n{3,}', '\n\n', display_text)

        # ── INTERACTIVE WEBVIEW BUTTON FORMATION ──────────────────────────────
        reply_markup = None
        for cid in chart_markers:
            from agent.tools_graficos import CHART_DIR
            json_path = os.path.join(CHART_DIR, f"chart_{cid}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as jf:
                        cy_data = jf.read().replace("\n", "").replace("\r", "")
                    
                    GRAPH_CACHE[cid] = cy_data
                    
                    encoded_bytes = base64.b64encode(cy_data.encode("utf-8"))
                    encoded_b64 = encoded_bytes.decode("ascii")
                    
                    title = "Red de Contratación"
                    resp_up = response.upper()
                    if "BID RIGGING" in resp_up or "MANIPULACIÓN DE LICITACIONES" in resp_up:
                        title = "Colusión Detectada (Bid Rigging)"
                    elif "RED DE PROVEEDORES" in resp_up or "REPRESENTACIÓN COMPARTIDA" in resp_up:
                        title = "Red de Proveedores (Representación Compartida)"
                    elif "COLUSION" in resp_up or "REPRESENTANTE" in resp_up:
                        title = "Análisis de Representación Compartida"
                    elif "CONSORCIO" in resp_up or "UNION TEMPORAL" in resp_up:
                        title = "Red de Consorcios"
                    
                    base_url = os.environ.get("WEBHOOK_URL") or "https://odin-bot-349527412949.us-central1.run.app"
                    if base_url.endswith("/"):
                        base_url = base_url[:-1]
                        
                    title_enc = urllib.parse.quote(title)
                    
                    # Telegram WebApp supports URLs up to ~8KB.
                    # Always prefer base64 inline (Cloud Run is stateless, cid breaks across instances).
                    # Fall back to cid only if URL exceeds Telegram limit.
                    url_b64 = f"{base_url}/visualizador?g={encoded_b64}&t={title_enc}"
                    if len(url_b64) <= 8000:
                        url = url_b64
                    else:
                        # Very large graph — must use cid endpoint (works if same instance serves)
                        url = f"{base_url}/visualizador?cid={cid}&t={title_enc}"
                    
                    # Create WebApp button
                    btn = InlineKeyboardButton(text="🔍 Ver Red Interactiva", web_app=WebAppInfo(url=url))
                    reply_markup = InlineKeyboardMarkup([[btn]])
                    
                    # Remove chart marker so we use WebView instead of static image text
                    display_text = display_text.replace(f"[CHART:{cid}]", "")
                    if cid in chart_paths:
                        del chart_paths[cid]
                    break  # Keep one interactive graph per bubble
                except Exception as ex_kb:
                    logger.error(f"Failed to create inline keyboard for graph {cid}: {ex_kb}")

        # Send text response
        if len(display_text) > 4000:
            for i in range(0, len(display_text), 4000):
                is_last = (i + 4000 >= len(display_text))
                markup = reply_markup if is_last else None
                await update.message.reply_text(display_text[i:i+4000], reply_markup=markup)
        else:
            await update.message.reply_text(display_text, reply_markup=reply_markup)

        # Auto-generate PDF (always if charts exist, or if user asked)
        has_data = len(response) > 200 or "$" in response or bool(chart_paths)
        is_just_question = response.strip().endswith("?") and len(response) < 300 and not has_data
        should_pdf = send_pdf or (bool(chart_paths) and not is_just_question)
        
        if should_pdf:
            try:
                await update.message.chat.send_action("upload_document")
                title = "Informe Odin"
                resp_up = response.upper()
                if "DIAGNOSTICO" in resp_up:
                    title = "Diagnostico de Riesgo"
                elif "EJECUCION" in resp_up or "PRESUPUEST" in resp_up:
                    title = "Ejecucion Presupuestal"
                elif "CONTRATISTA" in resp_up or "PROVEEDOR" in resp_up:
                    title = "Perfil de Contratista"
                elif "MONOPOL" in resp_up or "CORRUPCION" in resp_up:
                    title = "Alerta Anticorrupcion"

                filepath = generate_pdf(response, title, chart_paths)
                with open(filepath, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename=f"odin_{title.lower().replace(' ', '_')}.pdf",
                        caption=f"📄 {title}",
                    )
                os.remove(filepath)
                # Cleanup chart files
                for cp in chart_paths.values():
                    try: os.remove(cp)
                    except: pass
                logger.info(f"PDF sent to {user_id} ({len(chart_paths)} charts)")
            except Exception as e:
                logger.error(f"PDF error: {e}", exc_info=True)
                await update.message.reply_text(
                    "⚠️ No pude generar el PDF. El informe ya fue enviado como texto."
                )

        # Send Excel file(s) if user requested
        if send_excel and excels_list:
            try:
                import pandas as pd
                import uuid
                await update.message.chat.send_action("upload_document")
                
                valid_excels = [fp for fp in excels_list if os.path.exists(fp)]
                
                if len(valid_excels) > 1:
                    merged_filename = f"reporte_completo_{uuid.uuid4().hex[:8]}.xlsx"
                    merged_filepath = os.path.join("temp_downloads", merged_filename)
                    with pd.ExcelWriter(merged_filepath, engine='openpyxl') as writer:
                        for i, filepath in enumerate(valid_excels):
                            try:
                                df = pd.read_excel(filepath)
                                sheet_name = f"Tabla_{i+1}"
                                df.to_excel(writer, sheet_name=sheet_name, index=False)
                            except Exception:
                                pass
                    if os.path.exists(merged_filepath):
                        with open(merged_filepath, "rb") as f:
                            await update.message.reply_document(
                                document=f,
                                filename=merged_filename,
                                caption="📊 Datos Exportados (Múltiples Tablas en un solo Excel)"
                            )
                        # Add to list so it gets deleted in finally block
                        excels_list.append(merged_filepath)
                elif len(valid_excels) == 1:
                    filepath = valid_excels[0]
                    with open(filepath, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename=os.path.basename(filepath),
                            caption="📊 Datos Exportados (Excel)"
                        )
                
                logger.info(f"Excel sent to {user_id} ({len(valid_excels)} tables merged/sent)")
            except Exception as e:
                logger.error(f"Excel send error: {e}", exc_info=True)
                await update.message.reply_text(
                    "⚠️ No pude enviar el archivo Excel con los datos."
                )

        logger.info(f"Done ({len(response)} chars)")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Hubo un error procesando tu consulta. Intenta de nuevo en unos segundos."
        )
    finally:
        generated_excels_var.reset(token)
        for filepath in excels_list:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to delete temp Excel file {filepath}: {e}")


async def doc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download a SECOP document by its ID."""
    if not context.args:
        await update.message.reply_text(
            "Usa: /doc ID_DOCUMENTO\n\n"
            "Ejemplo: /doc 692865276\n\n"
            "Obtiene IDs preguntando:\n"
            '"Lista documentos del contrato CO1.PCCNTR.1234567"'
        )
        return

    doc_id = context.args[0].strip()
    filename = context.args[1] if len(context.args) > 1 else f"secop_doc_{doc_id}.pdf"

    await update.message.reply_text(f"⏳ Descargando documento {doc_id}...")
    await update.message.chat.send_action("upload_document")

    filepath = await download_secop_document(doc_id, filename)
    if filepath and os.path.exists(filepath):
        size_mb = os.path.getsize(filepath) / 1e6
        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f, filename=filename,
                caption=f"📎 Documento SECOP {doc_id} ({size_mb:.1f} MB)",
            )
        os.remove(filepath)
    else:
        link = f"https://community.secop.gov.co/Public/Tendering/ContractNoticePhases/View?PPI=CO1.PPI.{doc_id}&isFromPublicArea=True&isModal=False"
        await update.message.reply_text(
            f"No pude descargar directamente.\nIntenta manualmente:\n{link}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*Comandos:*\n"
        "/start - Bienvenida\n"
        "/doc `ID` - Descarga documento SECOP\n"
        "/reset - Borra el historial y empieza de cero\n"
        "/help - Esta ayuda\n\n"
        '*Para PDF*, agrega "pdf" o "informe" a tu pregunta:\n'
        '_"Dame un informe en pdf del diagnostico de INVIAS"_\n\n'
        "*Ejemplos:*\n"
        '🔴 "Diagnóstico de riesgo de la Registraduría"\n'
        '📊 "Ejecución presupuestal de Antioquia 2025 en pdf"\n'
        '📈 "Perfil del proveedor 830144531"\n'
        '📄 "Lista documentos del contrato CO1.PCCNTR.1855413"\n'
        '🔮 "Predice la demanda de software para 2026"\n'
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ── Web Application Route Handlers ────────────────────────────────────────

async def handle_health(request):
    return web.Response(text="OK - Odin Bot Running")


async def handle_visualizador(request):
    """Serve the interactive cytoscape network page."""
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates", "visualizador.html"
        )
        if os.path.exists(template_path):
            return web.FileResponse(template_path)
        else:
            return web.Response(text="visualizador.html template not found", status=404)
    except Exception as e:
        logger.error(f"Error serving visualizador: {e}", exc_info=True)
        return web.Response(text="Error loading visualizador page", status=500)

async def handle_chart_json(request):
    """Serve the chart JSON file."""
    try:
        cid = request.match_info.get('cid', '')
        # Basic validation to prevent directory traversal
        if not cid or not cid.isalnum():
            return web.Response(status=404)
            
        # 1. Try serving from memory cache (ideal for stateless Cloud Run if on same instance)
        if cid in GRAPH_CACHE:
            return web.Response(text=GRAPH_CACHE[cid], content_type="application/json")
        
        # 2. Fallback to disk (might be empty if Cloud Run scaled to new instance)
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent", "charts", f"chart_{cid}.json")
        if os.path.exists(json_path):
            return web.FileResponse(json_path)
            
        return web.Response(status=404)
    except Exception as e:
        logger.error(f"Error serving chart json: {e}")
        return web.Response(status=500)


def main():
    logger.info("Starting Odin Telegram Bot Unified Server...")

    # Re-create/fix document views on startup
    try:
        from scripts.fix_archivos_views import run as run_fix_views
        logger.info("Verifying and repairing BigQuery document views...")
        run_fix_views()
    except Exception as ex:
        logger.error(f"Failed to auto-repair BigQuery document views: {ex}", exc_info=True)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("doc", doc_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    webhook_url = os.environ.get("WEBHOOK_URL")
    processed_update_ids = set()
    active_update_ids = set()

    async def handle_webhook(request):
        try:
            data = await request.json()
            update = Update.de_json(data, app.bot)
            up_id = update.update_id
            
            logger.info(f"Received webhook update ID: {up_id}")
            
            if up_id in active_update_ids or up_id in processed_update_ids:
                logger.info(f"Ignoring duplicate webhook retry for update ID: {up_id}")
                return web.Response(text="OK")
            
            active_update_ids.add(up_id)
            try:
                # Process update synchronously in order to complete before returning 200 OK
                await app.process_update(update)
                processed_update_ids.add(up_id)
                if len(processed_update_ids) > 500:
                    processed_update_ids.discard(min(processed_update_ids))
            finally:
                active_update_ids.discard(up_id)
                
            logger.info(f"Finished processing webhook update ID: {up_id}")
        except Exception as e:
            logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return web.Response(text="OK")

    # ── CRON PUSH NOTIFICATIONS FOR DAILY OPPORTUNITIES ───────────────────────
    async def handle_cron_alertas(request):
        logger.info("Cron push notification endpoint triggered.")
        try:
            # Get all sessions stored in BQ
            sql_sess = f"SELECT session_key, session_json FROM `{session_service.table_ref}`"
            session_rows = list(client.query(sql_sess).result())
            
            if not session_rows:
                logger.info("No active sessions found for alerts.")
                return web.Response(text="No active sessions found in database.")
                
            # Search for active opportunities published in last 24h
            sql_cand = f"""
            SELECT id_del_proceso, nombre_del_procedimiento AS objeto, nombre_entidad AS entidad,
                   modalidad_de_contratacion AS modalidad, precio_base, fecha_de_publicacion_del_proceso AS publicado,
                   codigo_principal_de_categoria AS unspsc, urlproceso AS url
            FROM `{PROJECT}.{DATASET}.procesos_contratacion`
            WHERE estado_del_procedimiento IN ('Publicado', 'Abierto')
              AND fecha_de_publicacion_del_proceso >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            """
            candidates = [dict(r) for r in client.query(sql_cand).result()]
            
            # Fallback to last 15 days if last 24h is empty (e.g. weekends or test DB updates)
            if not candidates:
                logger.info("No processes in last 24 hours. Falling back to last 15 days...")
                sql_cand_fb = f"""
                SELECT id_del_proceso, nombre_del_procedimiento AS objeto, nombre_entidad AS entidad,
                       modalidad_de_contratacion AS modalidad, precio_base, fecha_de_publicacion_del_proceso AS publicado,
                       codigo_principal_de_categoria AS unspsc, urlproceso AS url
                FROM `{PROJECT}.{DATASET}.procesos_contratacion`
                WHERE estado_del_procedimiento IN ('Publicado', 'Abierto')
                  AND fecha_de_publicacion_del_proceso >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 DAY)
                ORDER BY fecha_de_publicacion_del_proceso DESC
                LIMIT 50
                """
                candidates = [dict(r) for r in client.query(sql_cand_fb).result()]
                
            if not candidates:
                logger.info("No active candidates found in BigQuery.")
                return web.Response(text="No candidates found in BQ.")

            sent_count = 0
            for s_row in session_rows:
                try:
                    s_key = s_row["session_key"]
                    s_json = s_row["session_json"]
                    parts = s_key.split(":")
                    if len(parts) < 2:
                        continue
                    chat_id = parts[1]
                    
                    if not chat_id.isdigit():
                        continue
                        
                    session_data = json.loads(s_json)
                    state = session_data.get("state", {})
                    
                    profile_nit = state.get("nit") or state.get("profile_nit")
                    profile_keywords = state.get("keywords") or state.get("profile_keywords")
                    
                    # Scan message history for profile indicators if empty
                    if not profile_nit and not profile_keywords:
                        events = session_data.get("events", [])
                        history_text = " ".join([str(e) for e in events]).lower()
                        if "830144531" in history_text or "espacios y redes" in history_text:
                            profile_nit = "830144531"
                        else:
                            # Default fallback profile (Espacios y Redes)
                            profile_nit = "830144531"
                            
                    matched_opts = []
                    
                    if profile_nit == "830144531":
                        past_categories = ['V1.81112100', 'V1.81112101', 'V1.83121703', 'V1.83121700']
                        past_entities = ["CENAC", "ICANH", "CULTURAS", "EJERCITO"]
                        
                        for c in candidates:
                            score = 0
                            reasons = []
                            obj_lower = (c.get("objeto") or "").lower()
                            ent_lower = (c.get("entidad") or "").lower()
                            unspsc = c.get("unspsc") or ""
                            
                            if any(pe.lower() in ent_lower for pe in past_entities):
                                score += 15
                                reasons.append("Entidad histórica coincidente")
                                
                            if unspsc in past_categories:
                                score += 12
                                reasons.append("Categoría UNSPSC coincidente")
                            elif unspsc.startswith("V1.8111") or unspsc.startswith("V1.8312"):
                                score += 6
                                reasons.append("Categoría UNSPSC relacionada")
                                
                            hits = [kw for kw in ["internet", "conectividad", "enlace", "redes", "canales"] if kw in obj_lower]
                            if hits:
                                score += len(hits) * 3
                                reasons.append(f"Palabras clave: {', '.join(hits)}")
                                
                            if score >= 10:
                                matched_opts.append({"process": c, "score": score, "reasons": reasons})
                    else:
                        kws = profile_keywords or ["internet", "tecnologia", "software"]
                        for c in candidates:
                            score = 0
                            reasons = []
                            obj_lower = (c.get("objeto") or "").lower()
                            hits = [kw for kw in kws if kw.lower() in obj_lower]
                            if hits:
                                score += len(hits) * 5
                                reasons.append(f"Palabras clave: {', '.join(hits)}")
                                
                            if score >= 5:
                                matched_opts.append({"process": c, "score": score, "reasons": reasons})
                                
                    if matched_opts:
                        matched_opts.sort(key=lambda x: x["score"], reverse=True)
                        top_matches = matched_opts[:3]
                        
                        msg = (
                            "🔔 **ALERTA DIARIA DE OPORTUNIDADES ODIN** 🔔\n\n"
                            "Hola! Encontré las siguientes oportunidades recomendadas para tu perfil comercial:\n\n"
                        )
                        for idx, m in enumerate(top_matches):
                            p = m["process"]
                            val = float(p.get("precio_base") or 0)
                            val_str = f"${val:,.0f} COP" if val > 0 else "No Definido"
                            msg += (
                                f"✨ **Oportunidad #{idx+1} (Score: {m['score']})**\n"
                                f"• **Entidad:** {p.get('entidad')}\n"
                                f"• **Objeto:** {p.get('objeto')[:120]}...\n"
                                f"• **Valor Estimado:** {val_str}\n"
                                f"• **Modalidad:** {p.get('modalidad')}\n"
                                f"• **Coincidencia:** {', '.join(m['reasons'])}\n"
                                f"• [Ver Proceso en SECOP II]({p.get('url')})\n\n"
                            )
                        
                        msg += "💡 _Puedes preguntarme detalles o analizar requisitos de cualquiera de estos procesos en Telegram._"
                        await app.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode="Markdown")
                        sent_count += 1
                except Exception as ex_user:
                    logger.error(f"Failed to send alert to user session {s_row['session_key']}: {ex_user}")
                    
            return web.Response(text=f"Cron alerts executed successfully. Messages sent: {sent_count}")
        except Exception as e:
            logger.error(f"Error in handle_cron_alertas: {e}", exc_info=True)
            return web.Response(text=f"Error in cron alerts: {e}", status=500)

    async def on_startup(web_app):
        await app.initialize()
        await app.start()
        if webhook_url:
            logger.info("Setting up Telegram webhook...")
            await app.bot.delete_webhook(drop_pending_updates=True)
            await app.bot.set_webhook(url=webhook_url)
            logger.info("Telegram webhook set successfully.")
        else:
            logger.info("Starting Telegram polling loop...")
            await app.bot.delete_webhook(drop_pending_updates=True)
            await app.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram polling loop started successfully.")

    async def on_cleanup(web_app):
        logger.info("Shutting down Application...")
        if not webhook_url:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Application shutdown complete.")

    web_app = web.Application()
    web_app.router.add_get("/", handle_health)
    web_app.router.add_get("/visualizador", handle_visualizador)
    web_app.router.add_get("/charts/{cid}.json", handle_chart_json)
    web_app.router.add_get("/cron/alertas", handle_cron_alertas)
    
    if webhook_url:
        web_app.router.add_post("/", handle_webhook)
        
    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)

    web.run_app(web_app, host="0.0.0.0", port=PORT, handle_signals=True)


if __name__ == "__main__":
    main()
