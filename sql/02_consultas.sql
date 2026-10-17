SET search_path=analisis,public;
-- Q1: numerador limitado a la caja; se informan ambas superficies.
CREATE VIEW q1 AS SELECT c.id,c.nombre,count(p.stop_id) paraderos,c.area_total_km2,c.area_estudio_km2,
 count(p.stop_id)/NULLIF(c.area_total_km2,0) densidad_comuna_completa,
 count(p.stop_id)/NULLIF(c.area_estudio_km2,0) densidad_area_observada
 FROM comunas c LEFT JOIN paraderos_gtfs p ON ST_Covers(c.geom,p.geom)
 AND c.id=(SELECT min(c2.id) FROM comunas c2 WHERE ST_Covers(c2.geom,p.geom))
 GROUP BY c.id,c.nombre,c.area_total_km2,c.area_estudio_km2;
CREATE TABLE cobertura_edificios AS SELECT e.id,e.comuna_id,e.punto geom,
 NOT EXISTS(SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(p.geom,e.punto,500)) sin_gtfs,
 NOT EXISTS(SELECT 1 FROM paraderos_osm p WHERE ST_DWithin(p.geom,e.punto,500)) sin_osm FROM edificios e;
CREATE INDEX idx_cobertura_geom ON cobertura_edificios USING gist(geom);
ANALYZE cobertura_edificios;
CREATE VIEW q2 AS SELECT c.nombre,count(e.id) edificios,
 count(*) FILTER(WHERE e.sin_gtfs) sin_gtfs,count(*) FILTER(WHERE e.sin_osm) sin_osm,
 100.0*count(*) FILTER(WHERE e.sin_gtfs)/NULLIF(count(e.id),0) pct_sin_gtfs,
 100.0*count(*) FILTER(WHERE e.sin_osm)/NULLIF(count(e.id),0) pct_sin_osm
 FROM comunas c LEFT JOIN cobertura_edificios e ON e.comuna_id=c.id GROUP BY c.id,c.nombre;
CREATE VIEW q3 AS SELECT 'GTFS sin OSM' fuente,count(*) total,
 count(*) FILTER(WHERE NOT EXISTS(SELECT 1 FROM paraderos_osm o WHERE ST_DWithin(o.geom,g.geom,50))) sin_pareja
 FROM paraderos_gtfs g UNION ALL SELECT 'OSM sin GTFS',count(*),
 count(*) FILTER(WHERE NOT EXISTS(SELECT 1 FROM paraderos_gtfs g WHERE ST_DWithin(g.geom,o.geom,50))) FROM paraderos_osm o;
-- Una geometría por shape, sin multiplicarla por sus viajes o rutas.
CREATE VIEW q4_base AS SELECT c.id,c.nombre,COALESCE(sum(ST_Length(ST_Intersection(c.geom,r.geom)))/1000,0) km_shapes
 FROM comunas c LEFT JOIN recorridos r ON ST_Intersects(c.geom,r.geom) GROUP BY c.id,c.nombre;
-- Unión por comuna y shape para no duplicar líneas coincidentes con bordes de subdivisión.
CREATE VIEW q4_sub AS WITH partes AS (
 SELECT c.id,r.shape_id,ST_UnaryUnion(ST_Collect(ST_Intersection(c.geom,r.geom))) geom
 FROM comunas_sub c JOIN recorridos r ON ST_Intersects(c.geom,r.geom) GROUP BY c.id,r.shape_id)
 SELECT c.id,c.nombre,COALESCE(sum(ST_Length(p.geom))/1000,0) km_shapes
 FROM comunas c LEFT JOIN partes p USING(id) GROUP BY c.id,c.nombre;
CREATE VIEW q5 AS SELECT re.route_short_name,p.stop_id,p.stop_name,a.id amenidad_id,a.nombre,a.amenity,
 ST_Distance(p.geom,a.geom) distancia_m
 FROM ruta_elegida re JOIN (SELECT DISTINCT route_id,stop_id FROM ruta_paradero) rp USING(route_id)
 JOIN paraderos_gtfs p USING(stop_id)
 CROSS JOIN LATERAL (SELECT * FROM salud a ORDER BY a.geom <-> p.geom LIMIT 1) a;
CREATE TABLE hexagonos AS SELECT h.i,h.j,ST_Intersection(h.geom,z.geom) geom
 FROM zona z CROSS JOIN LATERAL ST_HexagonGrid(500,z.geom) h WHERE ST_Intersects(z.geom,h.geom)
 AND ST_Area(ST_Intersection(h.geom,z.geom))>0;
ALTER TABLE hexagonos ADD PRIMARY KEY(i,j);
CREATE INDEX idx_hexagonos_geom ON hexagonos USING gist(geom);
ANALYZE hexagonos;
-- El lado del hexágono mide 500 m; ST_Covers asigna bordes una sola vez.
CREATE MATERIALIZED VIEW mv_grilla AS SELECT h.i,h.j,h.geom,
 (SELECT count(*) FROM edificios e WHERE ST_Covers(h.geom,e.punto)
 AND (h.i,h.j)=(SELECT h2.i,h2.j FROM hexagonos h2 WHERE ST_Covers(h2.geom,e.punto) ORDER BY h2.i,h2.j LIMIT 1)) edificios,
 (SELECT count(DISTINCT sr.route_id) FROM recorridos r JOIN shape_ruta sr USING(shape_id)
 WHERE ST_Intersects(h.geom,r.geom)) rutas FROM hexagonos h;
CREATE INDEX idx_mv_grilla_geom ON mv_grilla USING gist(geom);
ANALYZE mv_grilla;
CREATE VIEW q6 AS SELECT i,j,edificios,rutas,edificios::float8/(1+rutas) prioridad
 FROM mv_grilla ORDER BY prioridad DESC,edificios DESC,rutas,i,j LIMIT 10;
-- Pregunta propia: diversidad funcional (Shannon) de usos en torno a paraderos.
-- Una amenidad puede describir varios entornos; no se suman como objetos únicos.
CREATE VIEW q7 AS WITH categorias AS (
 SELECT p.stop_id,a.amenity,count(*) n FROM paraderos_gtfs p JOIN amenidades a
 ON ST_DWithin(a.geom,p.geom,300) GROUP BY p.stop_id,a.amenity),
 proporciones AS (SELECT *,n::float8/sum(n) OVER(PARTITION BY stop_id) proporcion FROM categorias),
 diversidad AS (SELECT stop_id,sum(n) amenidades,count(*) categorias,
 -sum(proporcion*ln(proporcion)) entropia_shannon FROM proporciones GROUP BY stop_id)
 SELECT p.stop_id,p.stop_name,coalesce(d.amenidades,0) amenidades,
 coalesce(d.categorias,0) categorias,coalesce(d.entropia_shannon,0) entropia_shannon
 FROM paraderos_gtfs p LEFT JOIN diversidad d USING(stop_id)
 ORDER BY entropia_shannon DESC,amenidades DESC,p.stop_id;
