"""Verificaciones semánticas sobre el resultado, sin valores esperados inventados."""
import json
from pathlib import Path
import psycopg2

def verificar(root=Path('/trabajo')):
    con=psycopg2.connect('dbname=tarea1 user=postgres host=127.0.0.1 password=tarea1local')
    cur=con.cursor();cur.execute('SET search_path=analisis,public')
    checks={
      'DPA oficial con 345 comunas':'SELECT count(*)=345 FROM public.comunas_cl',
      'GTFS presente':'SELECT count(*)>0 FROM paraderos_gtfs',
      'Edificios presentes':'SELECT count(*)>0 FROM edificios',
      'Servicios de salud presentes':'SELECT count(*)>0 FROM salud',
      'Sin polígonos OSM inválidos':'SELECT NOT EXISTS(SELECT 1 FROM public.osm_poligonos WHERE NOT ST_IsValid(geom))',
      'Asignación de paraderos única y completa':'SELECT (SELECT sum(paraderos) FROM q1)=(SELECT count(*) FROM paraderos_gtfs)',
      'Cobertura no pierde edificios asignados':'SELECT (SELECT sum(edificios) FROM q2)=(SELECT count(*) FROM edificios WHERE comuna_id IS NOT NULL)',
      'Grilla asigna cada edificio una vez':'SELECT (SELECT sum(edificios) FROM mv_grilla)=(SELECT count(*) FROM edificios)',
      'Coberturas dentro de 0 a 100':'SELECT NOT EXISTS(SELECT 1 FROM q2 WHERE pct_sin_gtfs NOT BETWEEN 0 AND 100 OR pct_sin_osm NOT BETWEEN 0 AND 100)',
      'Q4 coincide con y sin subdivisión':'SELECT coalesce(max(abs(a.km_shapes-b.km_shapes)),1)<0.001 FROM q4_base a JOIN q4_sub b USING(id)',
      'Todos los shapes derivan de rutas GTFS':'SELECT NOT EXISTS(SELECT 1 FROM recorridos r WHERE NOT EXISTS(SELECT 1 FROM shape_ruta s WHERE r.shape_id=s.shape_id))',
      'Q5 devuelve todos los paraderos de la ruta elegida':'SELECT (SELECT count(*) FROM q5)=(SELECT count(DISTINCT rp.stop_id) FROM ruta_paradero rp JOIN ruta_elegida r USING(route_id))',
      'Q7 caracteriza todos los paraderos':'SELECT (SELECT count(*) FROM q7)=(SELECT count(*) FROM paraderos_gtfs)',
      'Puntos GTFS sólo dentro de la caja':'SELECT NOT EXISTS(SELECT 1 FROM paraderos_gtfs p CROSS JOIN zona z WHERE NOT ST_Covers(z.geom,p.geom))'
    }
    result={}
    for name,query in checks.items():
        cur.execute(query);result[name]=bool(cur.fetchone()[0])
    (root/'resultados'/'verificacion.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    con.close()
    if not all(result.values()):raise RuntimeError(str(result))
    print('Verificación semántica OK:',len(result),'controles.')

if __name__=='__main__':verificar()
