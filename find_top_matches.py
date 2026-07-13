import os
from google.cloud import bigquery

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
client = bigquery.Client()

def find_matches():
    # We want to find active processes related to:
    # 1. Internet / Telecommunications / Networks (LOWER(nombre_del_procedimiento) LIKE '%internet%' OR '%redes%' OR '%conectividad%' OR '%telecomunicac%')
    # 2. Or UNSPSC Category starting with 'V1.811121' or 'V1.831217'
    # 3. Filtered to status: 'Publicado', 'Abierto', 'Evaluación'
    # We will score them based on:
    # - Entity overlap (10 points if entity is CENAC or ICANH or other past entities)
    # - Category overlap (10 points if UNSPSC category matches their top past categories)
    # - Text overlap (10 points if object has keywords like "internet", "enlaces", "conectividad", "canales dedicated", "redes")
    # - Price overlap (5 points if estimated price is similar to past contracts: average value ~50M to 200M, let's say between 10M and 500M)
    
    sql_active = """
    SELECT 
      id_del_proceso,
      nombre_del_procedimiento AS objeto,
      nombre_entidad AS entidad,
      modalidad_de_contratacion AS modalidad,
      estado_del_procedimiento AS estado,
      precio_base,
      fecha_de_publicacion_del_proceso AS publicado,
      codigo_principal_de_categoria AS unspsc,
      urlproceso AS url
    FROM `odin-v2-495523.secop.procesos_contratacion`
    WHERE estado_del_procedimiento IN ('Publicado', 'Abierto', 'Evaluación')
      AND fecha_de_publicacion_del_proceso >= CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) AS TIMESTAMP)
      AND (
        codigo_principal_de_categoria LIKE 'V1.811121%'
        OR codigo_principal_de_categoria LIKE 'V1.831217%'
        OR REGEXP_CONTAINS(LOWER(nombre_del_procedimiento), 'internet|conectividad|enlace|redes|telecomunicac')
      )
    ORDER BY fecha_de_publicacion_del_proceso DESC
    LIMIT 200
    """
    
    print("Running matching query...")
    active_processes = list(client.query(sql_active).result())
    print(f"Retrieved {len(active_processes)} active candidates.")
    
    # Let's define the scoring
    past_entities = [
        "CENAC AVIACION",
        "CENTRAL ADMINISTRATIVA Y CONTABLE ESPECIALIZADA CENAC EDUCACION",
        "ICANH",
        "CENTRAL ADMINISTRATIVA Y CONTABLE TELEMATICA",
        "CENTRAL ADMINISTRATIVA Y CONTABLE ESPECIALIZADA INTELIGENCIA",
        "ALCALDIA MUNICIPIO DE CAJICA",
        "MINISTERIO DE LAS CULTURAS",
        "DIRECCION DE INVESTIGACION CRIMINAL",
        "COMISION DE REGULACION DE ENERGIA Y GAG"
    ]
    past_categories = ['V1.81112100', 'V1.81112101', 'V1.83121703', 'V1.83121700']
    
    scored_matches = []
    for p in active_processes:
        score = 0
        reasons = []
        
        # 1. Entity similarity
        ent_lower = p.entidad.lower()
        has_past_entity = False
        for pe in past_entities:
            if pe.lower() in ent_lower or ent_lower in pe.lower():
                has_past_entity = True
                break
        
        if has_past_entity:
            score += 15
            reasons.append("Relación histórica sólida con la entidad compradora (CENAC/Ejército o afiliados)")
        elif "cenac" in ent_lower or "ejercito" in ent_lower or "defensa" in ent_lower:
            score += 8
            reasons.append("Entidad del sector Defensa (donde tienes el 70% de tus contratos históricos)")
            
        # 2. Category similarity (UNSPSC)
        if p.unspsc in past_categories:
            score += 12
            reasons.append(f"Categoría UNSPSC coincidente ({p.unspsc}): Servicios de Internet y Redes")
        elif p.unspsc and (p.unspsc.startswith("V1.8111") or p.unspsc.startswith("V1.8312")):
            score += 6
            reasons.append(f"Categoría UNSPSC altamente relacionada ({p.unspsc})")
            
        # 3. Object Keyword similarity
        obj_lower = p.objeto.lower()
        keyword_hits = []
        for kw in ["internet", "conectividad", "enlace", "redes", "canales", "redundante"]:
            if kw in obj_lower:
                keyword_hits.append(kw)
        
        if keyword_hits:
            score += len(keyword_hits) * 3
            reasons.append(f"Coincidencia de palabras clave en el objeto: {', '.join(keyword_hits)}")
            
        # 4. Price range (between 10M and 300M is ideal, above 300M is also okay but higher competition)
        price = 0
        try:
            price = float(p.precio_base)
        except Exception:
            pass
            
        if 10000000 <= price <= 250000000:
            score += 5
            reasons.append("Presupuesto en tu rango óptimo de adjudicación histórica ($10M - $250M COP)")
        elif price > 250000000:
            score += 2
            reasons.append("Presupuesto de gran escala (mayor valor, pero mayor competencia)")
            
        if score > 0:
            scored_matches.append({
                'process': p,
                'score': score,
                'reasons': reasons
            })
            
    # Sort matches by score descending
    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n--- TOP MATCHES ---")
    for idx, match in enumerate(scored_matches[:5]):
        p = match['process']
        print(f"\nRANK {idx+1} (Score: {match['score']})")
        print(f"ID: {p.id_del_proceso}")
        print(f"Entidad: {p.entidad}")
        print(f"Objeto: {p.objeto}")
        print(f"Valor: ${float(p.precio_base):,.0f} COP")
        print(f"UNSPSC: {p.unspsc}")
        print(f"Modalidad: {p.modalidad} | Estado: {p.estado}")
        print(f"Razones: {', '.join(match['reasons'])}")
        print(f"URL: {p.url}")

if __name__ == "__main__":
    find_matches()
