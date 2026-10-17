"""ETL y entrega completa dentro del contenedor. Reejecución sobre esquema propio."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile
import psycopg2
from psycopg2 import sql

ROOT=Path('/trabajo')
OUT=ROOT/'resultados'
SRC=ROOT/'datos_fuente'
DATA=ROOT/'datos'
DSN='dbname=tarea1 user=postgres host=127.0.0.1 password=tarea1local'
PG='PG:'+DSN

def run(args):
    print('Ejecutando:',args[0],flush=True)
    subprocess.run(args,check=True)

def finalizar():
    # El driver GeoJSON no implementa DeleteLayer: reemplazar nuestro archivo.
    for name in ('mv_grilla','comunas','cobertura_edificios'):
        destination=OUT/(name+'.geojson')
        destination.unlink(missing_ok=True)
        run(['ogr2ogr','-f','GeoJSON',str(destination),PG,
             '-sql',f'SELECT * FROM analisis.{name}','-t_srs','EPSG:4326'])
    from verificar import verificar
    verificar(ROOT)
    from informe import generar
    generar(ROOT)
    print('Entrega generada en resultados/.',flush=True)

def main():
    OUT.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
    if '--solo-salidas' in sys.argv:
        finalizar()
        return
    pbf=SRC/'chile-latest.osm.pbf'
    zips=[p for p in SRC.glob('*.zip') if p.name.lower().startswith('gtfs')]
    dpa=SRC/'DPA_2023.zip'
    for p in (pbf,dpa):
        if not p.exists(): raise SystemExit('Falta fuente: '+str(p))
    if len(zips)!=1: raise SystemExit('Debe existir exactamente un GTFS*.zip en datos_fuente')
    gtfs=zips[0]
    manifest=json.loads((SRC/'fuentes.json').read_text()) if (SRC/'fuentes.json').exists() else {}
    for p in (pbf,gtfs,dpa):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
        manifest.setdefault(p.name,{})
        manifest[p.name].update(bytes=p.stat().st_size,sha256=h.hexdigest())
    (OUT/'fuentes.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    con=psycopg2.connect(DSN); con.autocommit=True
    cur=con.cursor()
    cur.execute('CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS hstore;')
    # Recorte por caja como Lab 05; el SQL aplica después el límite exacto.
    gpkg=DATA/'osm_santiago-centro.gpkg'
    run(['ogr2ogr','-overwrite','-f','GPKG',str(gpkg),str(pbf),'points','lines','multipolygons',
         '-spat','-70.75','-33.52','-70.52','-33.36','-t_srs','EPSG:5361',
         '--config','OSM_MAX_TMPFILE_SIZE','512'])
    for layer,table in [('points','osm_puntos'),('lines','osm_lineas'),('multipolygons','osm_poligonos')]:
        run(['ogr2ogr','-overwrite','-f','PostgreSQL',PG,str(gpkg),layer,'-nln',table,
             '-lco','GEOMETRY_NAME=geom','-lco','FID=id','-lco','SPATIAL_INDEX=GIST',
             '-lco','COLUMN_TYPES=other_tags=hstore','-nlt','PROMOTE_TO_MULTI' if layer=='multipolygons' else 'GEOMETRY'])
    # Se extraen sólo los miembros del shapefile; sin extraer rutas arbitrarias del ZIP.
    with zipfile.ZipFile(dpa) as z:
        members=[n for n in z.namelist() if Path(n).stem.upper() in ('COMUNAS','COMUNAS_V1') and Path(n).suffix.lower() in ('.shp','.shx','.dbf','.prj','.cpg')]
        for n in members: (DATA/('COMUNAS'+Path(n).suffix.lower())).write_bytes(z.read(n))
    if not (DATA/'COMUNAS.shp').exists(): raise SystemExit('DPA no contiene COMUNAS.shp')
    run(['ogr2ogr','-overwrite','-f','PostgreSQL',PG,str(DATA/'COMUNAS.shp'),'-nln','comunas_cl',
         '-s_srs','EPSG:5360','-t_srs','EPSG:5361','-lco','GEOMETRY_NAME=geom','-lco','SPATIAL_INDEX=GIST','-nlt','MULTIPOLYGON'])
    # COPY por flujo: memoria acotada, incluso con millones de stop_times.
    raw_counts={}
    with zipfile.ZipFile(gtfs) as z:
        for name in ('stops','shapes','routes','trips','stop_times'):
            member=next(n for n in z.namelist() if Path(n).name==name+'.txt')
            with z.open(member) as f:
                columns=next(csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',newline='')))
            table='gtfs_'+name
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {} CASCADE').format(sql.Identifier(table)))
            cur.execute(sql.SQL('CREATE TABLE {} ({})').format(sql.Identifier(table),sql.SQL(',').join(sql.SQL('{} text').format(sql.Identifier(c)) for c in columns)))
            with z.open(member) as f:
                stream=io.TextIOWrapper(f,encoding='utf-8-sig',newline='')
                cur.copy_expert(sql.SQL('COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)').format(sql.Identifier(table)).as_string(con),stream)
            cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
            raw_counts[table]=cur.fetchone()[0]
    for path in ('01_etl.sql','02_consultas.sql'):
        print('Procesando '+path,flush=True)
        cur.execute((ROOT/'sql'/path).read_text(encoding='utf-8'))
        print('Completado '+path,flush=True)
    cur.execute('SET search_path=analisis,public')
    results={}
    for n in range(1,8):
        print('Resultado Q'+str(n),flush=True)
        query='SELECT * FROM q'+str(n) + ('_base' if n==4 else '')
        cur.execute(query)
        cols=[c.name for c in cur.description]; rows=cur.fetchall()
        results['q'+str(n)]=[dict(zip(cols,r)) for r in rows]
        with (OUT/f'q{n}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f); w.writerow(cols); w.writerows(rows)
    queries={
      'q1':'SELECT * FROM q1',
      'q2':"SELECT e.id FROM edificios e WHERE NOT EXISTS(SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(p.geom,e.punto,500))",
      'q4_base':'SELECT * FROM q4_base', 'q4_sub':'SELECT * FROM q4_sub',
      'q5':'SELECT * FROM q5', 'q6':'SELECT * FROM q6'}
    plans={}
    for name,q in queries.items():
        print('Plan y mediciones '+name,flush=True)
        samples=[]
        for _ in range(4):
            cur.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q); samples.append(cur.fetchone()[0][0])
        plans[name]={'primera_ms':samples[0]['Execution Time'],
                     'mediana_caliente_ms':sorted(s['Execution Time'] for s in samples[1:])[1],
                     'plan':samples[-1]}
        (OUT/(name+'_plan.json')).write_text(json.dumps(plans[name],indent=2))
    cur.execute('SELECT max(abs(a.km_shapes-b.km_shapes)) FROM q4_base a JOIN q4_sub b USING(id)')
    difference=cur.fetchone()[0]
    if difference is None or difference>0.001: raise RuntimeError('Q4 no coincide: '+str(difference))
    cur.execute("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='analisis' ORDER BY tablename,indexname")
    indexes=cur.fetchall()
    cur.execute("SELECT relname,indexrelname,idx_scan FROM pg_stat_user_indexes WHERE schemaname='analisis' ORDER BY idx_scan,indexrelname")
    usage=cur.fetchall()
    cur.execute('SELECT * FROM reparaciones'); repairs=[dict(zip([c.name for c in cur.description],r)) for r in cur.fetchall()]
    counts={}
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='analisis'")
    for (t,) in cur.fetchall():
        cur.execute(sql.SQL('SELECT count(*) FROM analisis.{}').format(sql.Identifier(t))); counts[t]=cur.fetchone()[0]
    cur.execute('SELECT count(*) FROM mv_grilla'); counts['mv_grilla']=cur.fetchone()[0]
    cur.execute('SELECT count(*) FROM edificios WHERE comuna_id IS NULL'); unassigned=cur.fetchone()[0]
    summary=dict(resultados=results,planes=plans,conteos=counts,crudas=raw_counts,indices=indexes,uso_indices=usage,reparaciones=repairs,diferencia_q4_km=difference,edificios_sin_comuna=unassigned)
    (OUT/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=str))
    inventory=['# Inventario medido','', '| Tabla | Filas |','|---|---:|']
    inventory += [f'| {t} | {n} |' for t,n in sorted({**counts,**raw_counts}.items())]
    inventory += ['','## Índices','']+[f'- `{t}.{i}`: `{definition}`' for t,i,definition in indexes]
    inventory += ['','## Reparaciones','',json.dumps(repairs,ensure_ascii=False),'',
      f'Edificios sin comuna: {unassigned}. Diferencia Q4: {difference} km.']
    (ROOT/'INVENTARIO.md').write_text('\n'.join(inventory),encoding='utf-8')
    with (OUT/'uso_indices.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['tabla','indice','lecturas']);w.writerows(usage)
    cur.execute('SELECT version(),postgis_full_version()')
    (OUT/'versiones.txt').write_text('\n'.join(cur.fetchone()),encoding='utf-8')
    for t in ('edificios','paraderos_gtfs','paraderos_osm','recorridos','comunas','salud'):
        cur.execute(sql.SQL('SELECT count(*) FROM analisis.{} WHERE ST_SRID(geom)<>5361 OR NOT ST_IsValid(geom) OR ST_IsEmpty(geom)').format(sql.Identifier(t)))
        if cur.fetchone()[0]: raise RuntimeError('Geometrías no válidas en '+t)
    con.close()
    finalizar()

if __name__=='__main__': main()
