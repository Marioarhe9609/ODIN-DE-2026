"""Odin v2 - Chart generation tools for the ADK agent.
The agent calls these tools with specific data to produce charts.
Each tool generates a PNG and returns a [CHART:uuid] marker.
"""
import os
import uuid
import tempfile

CHART_DIR = os.path.join(tempfile.gettempdir(), "odin_charts")
os.makedirs(CHART_DIR, exist_ok=True)

# Odin dark theme constants
BG = '#0f172a'
SURFACE = '#1e293b'
BORDER = '#334155'
MUTED = '#94a3b8'
WHITE = '#f8fafc'
PALETTE = ['#6366f1','#22c55e','#f97316','#ef4444','#06b6d4','#a855f7','#eab308','#ec4899',
           '#14b8a6','#f43f5e','#8b5cf6','#84cc16']


def _setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _save(fig, plt):
    cid = str(uuid.uuid4())[:8]
    path = os.path.join(CHART_DIR, f"chart_{cid}.png")
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return f"[CHART:{cid}]"


def generar_grafico_barras(titulo: str, etiquetas: str, valores: str, horizontal: bool = True) -> str:
    """Genera un grafico de barras comparativo. Usar para comparar valores entre categorias,
    rankings, presupuestos (asignado vs pagado), top proveedores, etc.
    Args:
        titulo: Titulo descriptivo del grafico.
        etiquetas: Nombres de las barras separados por coma. Ej: "Asignado,Pagado,Pendiente"
        valores: Valores numericos separados por coma. Ej: "101453,27364,74088"
        horizontal: True para barras horizontales (mejor para nombres largos), False para verticales.
    Returns:
        Marcador [CHART:id] para incrustar en la respuesta.
    """
    plt = _setup()
    labels = [l.strip() for l in etiquetas.split(",")]
    vals = [float(v.strip()) for v in valores.split(",")]
    n = len(labels)
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]

    fig, ax = plt.subplots(figsize=(7, max(1.8, n * 0.45)))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    if horizontal:
        bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.55, edgecolor='none')
        for bar, v in zip(bars, vals[::-1]):
            fmt = f'${v:,.0f}M' if v >= 1000 else f'{v:,.1f}'
            ax.text(bar.get_width() + max(vals)*0.02, bar.get_y()+bar.get_height()/2,
                    fmt, va='center', color=WHITE, fontsize=7, fontweight='bold')
    else:
        bars = ax.bar(labels, vals, color=colors, width=0.55, edgecolor='none')
        for bar, v in zip(bars, vals):
            fmt = f'${v:,.0f}M' if v >= 1000 else f'{v:,.1f}'
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(vals)*0.02,
                    fmt, ha='center', color=WHITE, fontsize=7, fontweight='bold')

    ax.set_title(titulo, color=WHITE, fontsize=10, fontweight='bold', pad=10)
    ax.tick_params(colors=MUTED, labelsize=8)
    for s in ['top','right']: ax.spines[s].set_visible(False)
    for s in ['bottom','left']: ax.spines[s].set_color(BORDER)
    plt.tight_layout(pad=1.5)
    marker = _save(fig, plt)
    return f"{marker} Grafico de barras generado: {titulo}"


def generar_grafico_dona(titulo: str, valor: float, maximo: float = 100, etiqueta_centro: str = "") -> str:
    """Genera un grafico de dona/rosquilla para mostrar un porcentaje o proporcion.
    Ideal para: porcentaje de ejecucion, scoring de riesgo, concentracion de mercado.
    Args:
        titulo: Titulo del grafico.
        valor: Valor actual (ej: 27 para 27% de ejecucion, o 65 para score de riesgo).
        maximo: Valor maximo de referencia (default 100).
        etiqueta_centro: Texto dentro de la dona. Si vacio, muestra el porcentaje.
    Returns:
        Marcador [CHART:id].
    """
    plt = _setup()
    pct = (valor / maximo * 100) if maximo > 0 else 0
    rest = maximo - valor

    # Color based on percentage
    if pct >= 70: color = '#22c55e'
    elif pct >= 40: color = '#f97316'
    else: color = '#ef4444'

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    fig.patch.set_facecolor(BG)
    ax.pie([valor, max(rest, 0)], colors=[color, BORDER], startangle=90,
           wedgeprops=dict(width=0.3, edgecolor='none'))
    ax.set_facecolor(BG)
    center = etiqueta_centro or f'{pct:.0f}%'
    ax.text(0, 0.05, center, ha='center', va='center', fontsize=22, fontweight='bold', color=WHITE)
    ax.text(0, -0.18, titulo, ha='center', va='center', fontsize=9, color=MUTED)
    plt.tight_layout(pad=0.5)
    marker = _save(fig, plt)
    return f"{marker} Grafico de dona generado: {titulo} ({pct:.0f}%)"


def generar_grafico_pastel(titulo: str, etiquetas: str, valores: str) -> str:
    """Genera un grafico de pastel/pie para distribuciones. Ideal para:
    distribucion por modalidad, por departamento, por tipo de contrato.
    Args:
        titulo: Titulo del grafico.
        etiquetas: Categorias separadas por coma. Ej: "Directa,Licitacion,Minima Cuantia"
        valores: Valores numericos separados por coma. Ej: "450,280,170"
    Returns:
        Marcador [CHART:id].
    """
    plt = _setup()
    labels = [l.strip() for l in etiquetas.split(",")]
    vals = [float(v.strip()) for v in valores.split(",")]
    n = len(labels)
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor(BG)
    wedges, texts, autotexts = ax.pie(vals, labels=None, colors=colors, autopct='%1.0f%%',
                                       startangle=90, pctdistance=0.75,
                                       wedgeprops=dict(edgecolor=BG, linewidth=2))
    for t in autotexts:
        t.set_color(WHITE)
        t.set_fontsize(8)
        t.set_fontweight('bold')
    ax.set_facecolor(BG)
    ax.set_title(titulo, color=WHITE, fontsize=11, fontweight='bold', pad=12)
    ax.legend(labels, loc='lower center', ncol=min(3, n), fontsize=7,
             facecolor=SURFACE, edgecolor=BORDER, labelcolor=MUTED,
             bbox_to_anchor=(0.5, -0.08))
    plt.tight_layout(pad=1)
    marker = _save(fig, plt)
    return f"{marker} Grafico de pastel generado: {titulo}"


def generar_grafico_lineas(titulo: str, etiquetas_x: str, nombres_series: str, valores_series: str) -> str:
    """Genera un grafico de lineas para tendencias temporales. Ideal para:
    evolucion mensual/anual de gasto, tendencia de contratacion, comparar periodos.
    Args:
        titulo: Titulo del grafico.
        etiquetas_x: Puntos del eje X separados por coma. Ej: "Ene,Feb,Mar,Abr,May"
        nombres_series: Nombres de cada linea separados por coma. Ej: "2024,2025"
        valores_series: Valores de cada serie separados por punto y coma, valores internos por coma.
                       Ej: "100,150,200,180,220;120,160,190,210,250"
    Returns:
        Marcador [CHART:id].
    """
    plt = _setup()
    x_labels = [l.strip() for l in etiquetas_x.split(",")]
    names = [n.strip() for n in nombres_series.split(",")]
    series = []
    for s in valores_series.split(";"):
        series.append([float(v.strip()) for v in s.split(",")])

    fig, ax = plt.subplots(figsize=(7, 3))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    for i, (name, vals) in enumerate(zip(names, series)):
        color = PALETTE[i % len(PALETTE)]
        ax.plot(x_labels[:len(vals)], vals, color=color, marker='o', markersize=4,
                linewidth=2, label=name)
        # Value labels on last point
        ax.annotate(f'{vals[-1]:,.0f}', (x_labels[len(vals)-1], vals[-1]),
                   textcoords="offset points", xytext=(8, 0),
                   color=color, fontsize=7, fontweight='bold')

    ax.set_title(titulo, color=WHITE, fontsize=10, fontweight='bold', pad=10)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.grid(True, alpha=0.15, color=MUTED)
    for s in ['top','right']: ax.spines[s].set_visible(False)
    for s in ['bottom','left']: ax.spines[s].set_color(BORDER)
    if len(names) > 1:
        ax.legend(fontsize=7, facecolor=SURFACE, edgecolor=BORDER, labelcolor=MUTED)
    plt.tight_layout(pad=1.5)
    marker = _save(fig, plt)
    return f"{marker} Grafico de lineas generado: {titulo}"


def generar_grafico_medidor(titulo: str, valor: float, minimo: float = 0, maximo: float = 100) -> str:
    """Genera un medidor/gauge semicircular para scores y niveles de riesgo. Ideal para:
    score de riesgo, nivel de concentracion, indice de transparencia.
    Args:
        titulo: Titulo del medidor.
        valor: Valor actual del indicador.
        minimo: Valor minimo de la escala (default 0).
        maximo: Valor maximo de la escala (default 100).
    Returns:
        Marcador [CHART:id].
    """
    plt = _setup()
    import numpy as np

    fig, ax = plt.subplots(figsize=(4, 2.5), subplot_kw={'projection': 'polar'})
    fig.patch.set_facecolor(BG)

    # Normalize to 0-1
    norm = (valor - minimo) / (maximo - minimo) if maximo > minimo else 0
    norm = max(0, min(1, norm))

    # Semicircle gauge
    theta_bg = np.linspace(np.pi, 0, 100)
    theta_val = np.linspace(np.pi, np.pi - (norm * np.pi), 100)

    ax.fill_between(theta_bg, 0.6, 1.0, color=BORDER, alpha=0.5)
    if norm >= 0.7: color = '#ef4444'
    elif norm >= 0.4: color = '#f97316'
    else: color = '#22c55e'
    ax.fill_between(theta_val, 0.6, 1.0, color=color)

    ax.set_ylim(0, 1.3)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis('off')
    ax.text(np.pi/2, 0.15, f'{valor:.0f}', ha='center', va='center',
           fontsize=26, fontweight='bold', color=WHITE)
    ax.text(np.pi/2, -0.25, titulo, ha='center', va='center',
           fontsize=9, color=MUTED)

    plt.tight_layout(pad=0.5)
    marker = _save(fig, plt)
    level = "CRITICO" if norm >= 0.7 else ("MEDIO" if norm >= 0.4 else "BAJO")
    return f"{marker} Medidor generado: {titulo} = {valor:.0f} ({level})"


def generar_red_consorcios(titulo: str, central_node: str, nodes: dict, edges: list) -> str:
    """Genera un grafo de red de consorcios usando matplotlib y retorna el token [CHART:id].
    Args:
        titulo: Titulo descriptivo del grafico.
        central_node: ID del nodo central (opcional). Si se provee, usa Star Layout.
        nodes: Diccionario de ID -> {"val": valor_total, "contr": num_contratos}
        edges: Lista de tuplas (origen, destino, consorcios_compartidos)
    """
    plt = _setup()
    import numpy as np

    # Identificar nodos unicos
    unique_nodes = list(nodes.keys())
    if not unique_nodes:
        # Retornar vacio si no hay nodos
        fig, ax = plt.subplots(figsize=(4, 4))
        fig.patch.set_facecolor(BG)
        ax.axis('off')
        return _save(fig, plt)

    # Posicionamiento de nodos
    pos = {}
    if central_node and central_node in unique_nodes:
        # Star layout
        pos[central_node] = (0.0, 0.0)
        others = [n for n in unique_nodes if n != central_node]
        n_others = len(others)
        for i, node in enumerate(others):
            theta = 2 * np.pi * i / n_others if n_others > 0 else 0
            pos[node] = (np.cos(theta), np.sin(theta))
    else:
        # Circular layout, intentamos mantener a las parejas juntas
        ordered_nodes = []
        visited = set()
        for edge in edges:
            u, v, w = edge
            if u not in visited:
                ordered_nodes.append(u)
                visited.add(u)
            if v not in visited:
                ordered_nodes.append(v)
                visited.add(v)
        for node in unique_nodes:
            if node not in visited:
                ordered_nodes.append(node)
        
        n_nodes = len(ordered_nodes)
        for i, node in enumerate(ordered_nodes):
            theta = 2 * np.pi * i / n_nodes
            pos[node] = (np.cos(theta), np.sin(theta))

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Dibujar enlaces
    max_weight = max(w for u, v, w in edges) if edges else 1
    for u, v, w in edges:
        if u in pos and v in pos:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            lw = 1 + 4 * (w / max_weight)
            ax.plot([x1, x2], [y1, y2], color='#6366f1', alpha=0.35, linewidth=lw, zorder=1)
            
            # Etiqueta del enlace en la mitad
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, f"{w}", color='#94a3b8', fontsize=6, ha='center', va='center',
                    bbox=dict(facecolor='#1e293b', edgecolor='none', alpha=0.8, boxstyle='round,pad=0.2'), zorder=2)

    # Dibujar nodos y etiquetas
    max_val = max(nodes[n].get('val', 0) or 0 for n in unique_nodes) if unique_nodes else 1
    for node in unique_nodes:
        x, y = pos[node]
        val = nodes[node].get('val', 0) or 0
        size_factor = (val / max_val) if max_val > 0 else 0
        size = 120 + size_factor * 300
        
        if node == central_node:
            color = '#f97316' # Naranja para el centro
            edgecolor = '#f8fafc'
        else:
            color = '#38bdf8' # Cian para socios
            edgecolor = '#334155'
            
        ax.scatter([x], [y], s=[size], color=color, edgecolors=edgecolor, linewidths=1.2, zorder=3)
        
        # Calcular offset para la etiqueta
        if x == 0 and y == 0:
            ox, oy = 0, -0.15
            ha, va = 'center', 'top'
        else:
            dist = np.sqrt(x*x + y*y)
            ox, oy = 0.12 * (x / dist), 0.12 * (y / dist)
            ha = 'left' if x > 0 else 'right'
            va = 'center'
            
        # Formatear etiqueta
        label = node[:16] + '...' if len(node) > 16 else node
        if val >= 1e12:
            val_str = f"${val/1e12:.1f}T COP"
        elif val >= 1e9:
            val_str = f"${val/1e9:.1f}B"
        elif val >= 1e6:
            val_str = f"${val/1e6:.1f}M"
        else:
            val_str = f"${val:,.0f}"
            
        contr = nodes[node].get('contr', 0)
        lbl_text = f"{label}\n{val_str}\n({contr} contr.)"
        
        ax.text(x + ox, y + oy, lbl_text, color='#f8fafc', fontsize=6, ha=ha, va=va,
                bbox=dict(facecolor='#1e293b', edgecolor='#334155', alpha=0.85, boxstyle='round,pad=0.2'), zorder=4)

    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.4, 1.4)
    ax.axis('off')
    ax.set_title(titulo, color=WHITE, fontsize=10, fontweight='bold', pad=12)
    plt.tight_layout(pad=1.5)
    
    marker = _save(fig, plt)
    
    try:
        import json
        cid = marker.replace("[CHART:", "").replace("]", "")
        cy_elements = []
        for node in unique_nodes:
            val = nodes[node].get('val', 0) or 0
            contr = nodes[node].get('contr', 0)
            if node == central_node:
                color = '#f97316'
                size = 45
            else:
                color = '#38bdf8'
                size = 30
                
            if val >= 1e12: val_str = f"${val/1e12:.1f}T COP"
            elif val >= 1e9: val_str = f"${val/1e9:.1f}B"
            elif val >= 1e6: val_str = f"${val/1e6:.1f}M"
            else: val_str = f"${val:,.0f} COP"
            
            cy_elements.append({
                "data": {
                    "id": node,
                    "label": node[:15] + '...' if len(node) > 15 else node,
                    "size": size,
                    "color": color,
                    "edgecolor": '#334155',
                    "val": val_str,
                    "contr": f"{contr} contratos"
                }
            })
            
        for u, v, w in edges:
            cy_elements.append({
                "data": {
                    "id": f"{u}_{v}",
                    "source": u,
                    "target": v,
                    "weight": w,
                    "label": f"{w} conexiones"
                }
            })
            
        json_path = os.path.join(CHART_DIR, f"chart_{cid}.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(cy_elements, jf, ensure_ascii=True, separators=(',', ':'))
    except Exception:
        pass
        
    return marker


def get_chart_path(chart_id: str) -> str:
    """Get the file path for a chart by its ID."""
    return os.path.join(CHART_DIR, f"chart_{chart_id}.png")


TOOLS = [
    generar_grafico_barras,
    generar_grafico_dona,
    generar_grafico_pastel,
    generar_grafico_lineas,
    generar_grafico_medidor,
    generar_red_consorcios,
]
