"""Odin v2 - PDF report generator. Embeds charts from agent tools."""
import os, re, tempfile
from datetime import datetime


def _safe_text(s):
    """Remove emojis, keep Spanish chars for latin-1."""
    emojis = {"\U0001f534":"[!]","\U0001f7e0":"[!]","\U0001f7e1":"[~]","\U0001f7e2":"[OK]",
              "\U0001f7e3":"[?]","\u26ab":"[-]","\U0001f535":"[i]","\u23f0":"[T]",
              "\U0001f4b0":"[$]","\u26d4":"[X]","\u2705":"[OK]","\u26a0":"[!]",
              "\U0001f536":"[!]","\U0001f4ca":"[D]","\U0001f4cb":"[R]","\U0001f50d":"[S]",
              "\U0001f4c4":"[F]","\U0001f4ce":"[A]","\u2b50":"[*]","\U0001f441":"[O]",
              "\U0001f6a8":"[!]","\U0001f3af":"[>]","\U0001f4b8":"[$]","\U0001f4b5":"[$]"}
    for em, rep in emojis.items():
        s = s.replace(em, rep)
    return s.encode("latin-1", errors="replace").decode("latin-1")

def _clean_md(s):
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)
    s = re.sub(r'\*(.*?)\*', r'\1', s)
    s = re.sub(r'`(.*?)`', r'\1', s)
    return s.strip()


def generate_pdf(text, title="Informe Odin", chart_paths=None):
    """Generate PDF with embedded charts from the agent.
    
    Args:
        text: Response text from the agent (may contain [CHART:id] markers).
        title: Report title.
        chart_paths: Dict mapping chart_id -> file_path (from extract_charts).
    """
    from fpdf import FPDF
    chart_paths = chart_paths or {}
    LM = 15

    pdf = FPDF()
    pdf.set_left_margin(LM)
    pdf.set_right_margin(15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_fill_color(99, 102, 241)
    pdf.rect(0, 30, 210, 1.2, "F")
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(6)
    pdf.cell(0, 9, _safe_text(title), ln=True, align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Odin v2 | SECOP II",
             ln=True, align="C")
    pdf.set_y(35)

    # Process content line by line
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(1.5)
            continue

        # Embed chart images
        chart_match = re.search(r'\[CHART:(\w+)\]', stripped)
        if chart_match:
            cid = chart_match.group(1)
            cpath = chart_paths.get(cid)
            if cpath and os.path.exists(cpath):
                pdf.set_x(LM)
                pdf.image(cpath, x=LM, w=180)
                pdf.ln(3)
            # Remove chart marker from text, render remaining text if any
            remaining = re.sub(r'\[CHART:\w+\]', '', stripped).strip()
            remaining = _safe_text(_clean_md(remaining))
            if remaining and len(remaining) > 5:
                pdf.set_font("Helvetica", "I", 7)
                pdf.set_text_color(148, 163, 184)
                pdf.set_x(LM)
                pdf.multi_cell(0, 3, remaining)
            continue

        txt = _safe_text(_clean_md(stripped))
        if not txt.strip():
            continue

        # Section headings
        if stripped.startswith("##"):
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(99, 102, 241)
            pdf.ln(2)
            pdf.set_x(LM)
            pdf.multi_cell(0, 4, _safe_text(stripped.lstrip("# ")))
            pdf.ln(1)
        elif stripped.startswith("#"):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 41, 59)
            pdf.ln(2)
            pdf.set_x(LM)
            pdf.multi_cell(0, 5, _safe_text(stripped.lstrip("# ")))
            pdf.ln(1)
        # Bold section labels
        elif stripped.startswith("**") and stripped.endswith("**"):
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(30, 41, 59)
            pdf.ln(1.5)
            pdf.set_x(LM)
            pdf.multi_cell(0, 4, txt)
            pdf.ln(1)
        # Bullet points
        elif stripped.startswith(("- ", "* ", "  -", "  *")):
            content = txt.lstrip("-* ").strip()
            if ":" in content:
                parts = content.split(":", 1)
                pdf.set_x(LM + 4)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(30, 41, 59)
                pdf.write(4, "- " + parts[0] + ": ")
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(71, 85, 105)
                pdf.multi_cell(0, 4, parts[1].strip())
            else:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(71, 85, 105)
                pdf.set_x(LM + 4)
                pdf.multi_cell(0, 4, "- " + content)
        # Alert lines
        elif txt.startswith(("[!", "[X", "[$", "[OK", "[D", "[R", "[~")):
            pdf.set_font("Helvetica", "B", 8)
            if txt.startswith("[!"):
                pdf.set_text_color(220, 38, 38)
            else:
                pdf.set_text_color(30, 41, 59)
            pdf.set_x(LM)
            pdf.multi_cell(0, 4, txt)
        # Normal text
        else:
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(71, 85, 105)
            pdf.set_x(LM)
            pdf.multi_cell(0, 4, txt)

    # Footer
    pdf.set_y(-12)
    pdf.set_draw_color(51, 65, 85)
    pdf.line(LM, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(1.5)
    pdf.set_font("Helvetica", "I", 6)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 3, "Odin v2 | Contratacion Publica Colombia | SECOP II | Generado automaticamente", align="C")

    path = os.path.join(tempfile.gettempdir(), f"odin_report_{os.getpid()}.pdf")
    pdf.output(path)
    return path
