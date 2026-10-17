"""Mapas y PDF de seis páginas a partir de resultados reales."""
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image

def generar(root):
    root=Path(root); out=root/'resultados'
    s=json.loads((out/'resumen.json').read_text()); q=s['resultados']
    features=json.loads((out/'mv_grilla.geojson').read_text())['features']
    communes=json.loads((out/'comunas.geojson').read_text())['features']
    def rings(g):
        if g['type']=='Polygon': return [g['coordinates'][0]]
        if g['type']=='MultiPolygon': return [p[0] for p in g['coordinates']]
        return []
    def decorate(ax):
        ax.set_xlim(-70.75,-70.52);ax.set_ylim(-33.52,-33.36)
        ax.set_aspect(1/math.cos(math.radians(33.44)))
        ax.set_xlabel('Longitud');ax.set_ylabel('Latitud');ax.tick_params(labelsize=7)
        ax.annotate('N',xy=(-70.535,-33.375),xytext=(-70.535,-33.395),ha='center',arrowprops={'arrowstyle':'->'})
        length=2000/(111320*math.cos(math.radians(33.44)))
        ax.plot([-70.735,-70.735+length],[-33.51,-33.51],c='black',lw=2)
        ax.text(-70.735,-33.507,'2 km aprox.',fontsize=7)
    fig,axs=plt.subplots(1,2,figsize=(10,4.6),constrained_layout=True)
    for ax,key,title in zip(axs,['edificios','rutas'],['Edificios por hexágono','Rutas GTFS distintas por hexágono']):
        patches=[];values=[]
        for f in features:
            for r in rings(f['geometry']): patches.append(Polygon(r));values.append(f['properties'][key])
        pc=PatchCollection(patches,cmap='YlOrRd' if key=='edificios' else 'viridis',edgecolors='#ffffff',linewidth=.15)
        pc.set_array(__import__('numpy').array(values));ax.add_collection(pc)
        selected={(r['i'],r['j']):n+1 for n,r in enumerate(q['q6'])}
        for f in features:
            cell=(f['properties']['i'],f['properties']['j'])
            if cell in selected:
                for ring in rings(f['geometry']):
                    ax.add_patch(Polygon(ring,fill=False,edgecolor='#1665d8',linewidth=1.2))
        fig.colorbar(pc,ax=ax,shrink=.7,label='Cantidad');ax.set_title(title,fontsize=11);decorate(ax)
    fig.suptitle('Santiago centro | grilla de lado 500 m\nOSM: 14-10-2026 · GTFS: V168.20261003',fontsize=12)
    fig.savefig(out/'mapa_grilla.png',dpi=190);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.6),constrained_layout=True)
    pct={r['nombre']:r for r in q['q2']}
    for ax,key,title in zip(axs,['pct_sin_gtfs','pct_sin_osm'],['Sin paradero GTFS a 500 m','Sin bus_stop OSM a 500 m']):
        patches=[];values=[]
        for f in communes:
            value=pct[f['properties']['nombre']][key]
            for ring in rings(f['geometry']):patches.append(Polygon(ring));values.append(float(value) if value is not None else float('nan'))
        pc=PatchCollection(patches,cmap='YlOrRd',edgecolors='#555555',linewidth=.5)
        pc.set_array(__import__('numpy').array(values));pc.set_clim(0,100);ax.add_collection(pc)
        fig.colorbar(pc,ax=ax,shrink=.7,label='% de edificios');ax.set_title(title,fontsize=11);decorate(ax)
    fig.suptitle('Cobertura por comuna dentro de la caja\nOSM: 14-10-2026 · GTFS: V168.20261003 · DPA: 2023',fontsize=12)
    fig.savefig(out/'mapa_cobertura.png',dpi=190);plt.close(fig)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySmall',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=7))
    styles.add(ParagraphStyle(name='Cell',fontName='Helvetica',fontSize=7.8,leading=9.4,spaceAfter=0))
    styles['Title'].fontSize=21;styles['Title'].leading=25
    styles['Heading1'].fontSize=15;styles['Heading1'].leading=18
    story=[]
    def p(text,style='BodySmall'): story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'Heading1')
    def table(headers,rows,widths=None):
        data=[[Paragraph('<b>'+escape(str(x))+'</b>',styles['Cell']) for x in headers]]
        for row in rows:
            data.append([Paragraph(escape(str(x)),styles['Cell']) for x in row])
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbe8ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#38586a')),('BOTTOMPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2)]))
        story.append(t);story.append(Spacer(1,6))
    def num(v,d=1): return '-' if v is None else f'{float(v):,.{d}f}'
    def page():story.append(PageBreak())
    p('Ciudad construida y transporte público','Title')
    p('Tarea 1 · PostGIS de punta a punta · Santiago centro','Heading2')
    p('<b>Nicolas Galaz · Martin Yañez · Eduardo Roa</b><br/>ELE051-B / EIN102B · USM 2026-2 · Paralelo 701')
    p('Caja: lon -70,75 a -70,52; lat -33,52 a -33,36. OSM al 14-10-2026; GTFS V168.20261003 (vigente desde 03-10-2026); DPA 2023. Descarga: 15-10-2026. Distancias euclidianas en EPSG:5361.')
    h('1 y 2. Paraderos, densidad y cobertura')
    rows=[]
    for r in sorted(q['q1'],key=lambda r:r['nombre']):
        c=next(x for x in q['q2'] if x['nombre']==r['nombre'])
        rows.append([r['nombre'],r['paraderos'],num(r['densidad_comuna_completa'],2),num(r['densidad_area_observada'],2),c['edificios'],num(c['pct_sin_gtfs']),num(c['pct_sin_osm'])])
    table(['Comuna','GTFS','/km² total','/km² caja','Edificios','% sin GTFS','% sin OSM'],rows,[116,43,58,58,55,65,65])
    worst=max((r for r in q['q2'] if r['pct_sin_gtfs'] is not None),key=lambda r:float(r['pct_sin_gtfs']))
    p(f"La mayor proporción sin GTFS es {escape(worst['nombre'])}: {num(worst['pct_sin_gtfs'])}%. Los denominadores son edificios OSM con punto interior en la caja y asignación comunal única; no representan hogares ni población.")
    p('La densidad sobre comuna completa es la solicitada, pero subestima zonas parcialmente observadas. La densidad sobre el área de la caja permite comparar con el mismo dominio. Al recortar paraderos a la caja se introduce efecto de borde: no se considera oferta inmediatamente exterior.')
    page();h('3. Dos fuentes, un objeto')
    table(['Comparación','Total','Sin pareja a 50 m','%'],[[r['fuente'],r['total'],r['sin_pareja'],num(100*r['sin_pareja']/r['total'] if r['total'] else None)] for r in q['q3']],[180,95,130,115])
    p('Las discrepancias miden concordancia espacial, no una tasa de error. GTFS declara infraestructura operativa y OSM registra lo cartografiado por colaboradores; coordenadas desplazadas, duplicados, fechas y criterios de parada explican parte de la diferencia. El borde también puede excluir parejas.')
    h('4. Kilómetros de trazados por comuna')
    table(['Comuna','km de shapes'],[[r['nombre'],num(r['km_shapes'],2)] for r in sorted(q['q4'],key=lambda r:r['nombre'])],[330,190])
    b=s['planes']['q4_base']['mediana_caliente_ms'];a=s['planes']['q4_sub']['mediana_caliente_ms']
    p(f"Sin subdivisión: {b:.2f} ms; con subdivisión: {a:.2f} ms. Factor base/subdivisión: {b/a:.2f}x. Mediana de tres ejecuciones calientes, tras una inicial; no es una garantía para otro equipo. Diferencia máxima: {float(s['diferencia_q4_km']):.8f} km.")
    p(('En esta ejecución la subdivisión reduce el tiempo.' if a<b else 'En esta ejecución la subdivisión aumenta el tiempo; generar partes y unirlas por shape cuesta más que el ahorro del filtro espacial.')+' La equivalencia del resultado se verifica independientemente de cuál estrategia sea más rápida.')
    p('Se suma cada shape una vez: variantes e ida/vuelta permanecen separadas, sin multiplicar por viajes. Son kilómetros de trazados declarados, no longitud vial única ni oferta ponderada por frecuencia. Las partes se unen por comuna y shape para no duplicar segmentos en bordes internos.')
    page();h('5. Salud más cercana en un recorrido')
    route=q['q5'][0]['route_short_name'] if q['q5'] else '(sin resultados)'
    p(f"Se eligió automáticamente la ruta {escape(route)}, con mayor número de paraderos distintos observados. La pertenencia se obtiene de trips + stop_times, cargado con COPY. Se conserva cada stop_id una sola vez por ruta.")
    table(['Paradero (10 más alejados)','Servicio OSM','Distancia m'],[[r['stop_id'],(r['nombre'] or r['amenity'])[:48],num(r['distancia_m'])] for r in sorted(q['q5'],key=lambda r:float(r['distancia_m']),reverse=True)[:10]],[110,305,105])
    if q['q5']:
        p(f"En {len(q['q5'])} paraderos, la distancia máxima al servicio de salud OSM más próximo es {max(float(r['distancia_m']) for r in q['q5']):.1f} m. Todas las filas están en q5.csv. No se mide acceso peatonal ni disponibilidad de atención; servicios fuera de la caja pueden estar más cerca.")
    h('7. Pregunta propia: diversidad funcional de entornos')
    p('¿Qué paraderos GTFS tienen un entorno con mayor mezcla de usos OSM? En un radio de 300 m se calcula la entropía de Shannon H=-sum(p ln p), donde p es la proporción de cada categoría amenity. H aumenta con la variedad y el equilibrio de usos; cero significa ausencia de amenidades o una sola categoría. Se informa el conteo para distinguir ambos casos.')
    table(['Paradero (10 con mayor H)','Amenidades','Categorías','H'],[[r['stop_id'],r['amenidades'],r['categorias'],num(r['entropia_shannon'],3)] for r in q['q7'][:10]],[230,90,90,110])
    if q['q7']:
        r=q['q7'][0];p(f"El entorno más diverso corresponde a {escape(r['stop_id'])}: {r['amenidades']} amenidades, {r['categorias']} categorías y H={float(r['entropia_shannon']):.3f}. Una amenidad puede caracterizar varios entornos; no se suman estos conteos como objetos únicos. La mezcla observada depende de la completitud temática de OSM y no prueba demanda ni causalidad.")
    page();h('6. Grilla: edificios y rutas distintas')
    story.append(Image(str(out/'mapa_grilla.png'),width=520,height=239))
    p('Cada celda es un hexágono de lado 500 m, recortado a la caja. Se cuentan puntos interiores de edificios y route_id distintos que intersectan la celda. Los contornos azules señalan el top 10 de la tabla. La vista materializada evita recalcular estos cruces para cada mapa.')
    table(['i','j','Edificios','Rutas','Prioridad'],[[r['i'],r['j'],r['edificios'],r['rutas'],num(r['prioridad'],2)] for r in q['q6']],[65,65,120,120,150])
    p('“Más edificios y menos recorridos” se operacionaliza con edificios/(1+rutas), orden descendente, desempate por edificios descendente y rutas ascendente. Es un criterio explícito de priorización; no un indicador validado de demanda. La tabla identifica las diez celdas y permite ubicarlas en mv_grilla.geojson mediante (i,j).')
    top=q['q6'][0];p(f"La primera celda es ({top['i']}, {top['j']}): {top['edificios']} edificios y {top['rutas']} rutas. Los polígonos pequeños recortados del borde no están normalizados por superficie y deben interpretarse con cautela.")
    page();h('Cobertura comparada e interpretación de planes')
    story.append(Image(str(out/'mapa_cobertura.png'),width=520,height=239))
    comparable=[r for r in q['q2'] if r['pct_sin_gtfs'] is not None]
    changes=sum((float(r['pct_sin_gtfs'])<float(r['pct_sin_osm'])) for r in comparable)
    p(f"En {changes} de {len(comparable)} comunas, GTFS deja un porcentaje menor de edificios sin paradero cercano que OSM. Los mapas usan la misma escala 0-100%; muestran porcentajes sólo para la porción observada de cada comuna.")
    p('<b>Planes reales.</b> Los archivos *_plan.json incluyen buffers, filas y tiempos. Los índices observados se extraen del árbol del plan; el planificador puede preferir escaneos secuenciales en capas pequeñas.')
    def scan(node):
        found=[]
        if 'Index Name' in node:found.append(node['Index Name'])
        for sub in node.get('Plans',[]):found+=scan(sub)
        return sorted(set(found))
    for key,explanation in [('q1','El GiST de paraderos_gtfs busca puntos dentro de cada comuna; el de comunas resuelve la asignación única de bordes. Sin ellos se examinan muchos más candidatos por cruce.'),('q2','La búsqueda interior es paraderos_gtfs: GiST filtra por caja expandida y ST_DWithin verifica 500 m. Sin el índice, se recorren paraderos por cada edificio.'),('q5','LATERAL ejecuta una búsqueda por paradero; el GiST de salud ordena vecinos con KNN. Sin él, se calculan y ordenan distancias a todos los servicios.')]:
        names=scan(s['planes'][key]['plan']['Plan'])
        p(f"<b>{key.upper()}</b> ({s['planes'][key]['mediana_caliente_ms']:.2f} ms): índices observados: {escape(', '.join(names) or 'ninguno')}. {explanation}")
    page();h('Decisiones del pipeline y límites')
    p('<b>Infraestructura.</b> Compose declara PostgreSQL 16 / PostGIS 3.5, GDAL y Python; volumen con nombre y montaje relativo. Un único cargar.py construye capas, consulta y exporta. El puerto local 5434 evita interferir con los laboratorios. Se reutilizan los patrones de los Labs 03-05, con implementación propia para GTFS y las preguntas.')
    p('<b>SRID.</b> Todo el análisis usa 5361 (SIRGAS-Chile / UTM 19S), con unidades métricas apropiadas para Santiago. OSM y GTFS provienen de 4326 y DPA de 5360. ST_Transform cambia coordenadas; ST_SetSRID sólo declara el sistema de los puntos GTFS. GeoJSON se exporta a 4326.')
    repair=s['reparaciones'][0]
    p(f"<b>Validez y representación.</b> OSM: {repair['invalidas_antes']} polígonos inválidos antes, {repair['invalidas_despues']} después de ST_MakeValid + extracción poligonal y ST_Multi; {repair['vacias_despues']} vacíos después, excluidos de derivados. Cada edificio usa ST_PointOnSurface, que permanece dentro incluso en polígonos cóncavos. La asignación comunal resuelve bordes con menor código; {s['edificios_sin_comuna']} edificios no se asignaron.")
    p(f"<b>GTFS y shapes múltiples.</b> COPY carga las cinco tablas crudas como texto. Se forma una LineString completa por shape_id ordenando shape_pt_sequence numérico y luego se recorta; filtrar vértices primero perdería segmentos de entrada/salida. Se excluyen {repair['shapes_sin_viaje_en_zona']} shapes de la caja que no aparecen en trips. La relación shape-ruta es una tabla distinta, pues un shape puede servir a varias rutas. Q4 suma shapes y Q6 cuenta route_id distintos; no se pondera por frecuencia.")
    p(f"<b>Escala.</b> stop_times: {s['crudas']['gtfs_stop_times']:,} filas cargadas por flujo, sin INSERT individual. Edificios: {s['conteos']['edificios']:,}; GTFS: {s['conteos']['paraderos_gtfs']:,}; OSM bus_stop: {s['conteos']['paraderos_osm']:,}; shapes recortados: {s['conteos']['recorridos']:,}. Inventario completo en INVENTARIO.md.")
    p('<b>Índices.</b> GiST en todas las geometrías derivadas, incluido el punto interior; B-tree en identificadores de enlace; ANALYZE final. La subdivisión se mide contra la misma consulta sin subdividir, verificando igualdad métrica. pg_stat_user_indexes es acumulativo y puede actualizarse con retraso: cero lecturas sólo significa ausencia de uso en esta ejecución.')
    unused=[r[1] for r in s['uso_indices'] if r[2]==0]
    p('<b>Sin lecturas registradas:</b> '+escape(', '.join(unused[:10]) or 'ninguno')+'. Ver uso_indices.csv para la lista completa; no se recomienda borrar índices sólo por esta observación.')
    p('<b>Dificultades resueltas.</b> La imagen Debian inicial devolvió 404 en repositorios y paquetes retirados; se resolvió con la variante Alpine del Lab 05 y herramientas declaradas. El DPA descargado denomina sus miembros COMUNAS_v1; el cargador lo admite explícitamente.')
    p('<b>Fuentes y alcance.</b> Geofabrik/OpenStreetMap (ODbL), DTPM/Red y DPA IDE Chile (CC-BY), con URLs, fechas y SHA-256 en fuentes.json. No se equiparan edificios con personas, proximidad con accesibilidad efectiva ni rutas con frecuencia. No se publica en GitHub por instrucción del equipo.')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#566773'))
        canvas.drawString(38,24,'Galaz · Yañez · Roa | Santiago centro | 15-10-2026')
        canvas.drawRightString(A4[0]-38,24,str(doc.page))
    SimpleDocTemplate(str(out/'Informe_Tarea1_PostGIS.pdf'),pagesize=A4,rightMargin=38,leftMargin=38,topMargin=30,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)

if __name__=='__main__':
    import sys
    generar(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
