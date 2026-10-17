CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;
DROP SCHEMA IF EXISTS analisis CASCADE;
CREATE SCHEMA analisis;
SET search_path=analisis,public;
-- Densificar antes de proyectar preserva los bordes geográficos curvos en UTM.
CREATE TABLE zona AS SELECT ST_Transform(ST_Segmentize(ST_MakeEnvelope(-70.75,-33.52,-70.52,-33.36,4326),0.001),5361)::geometry(Polygon,5361) geom;
CREATE TABLE reparaciones AS
 SELECT 'osm_poligonos'::text tabla, count(*) FILTER(WHERE NOT ST_IsValid(geom)) invalidas_antes,
 count(*) FILTER(WHERE ST_IsEmpty(geom)) vacias_antes FROM public.osm_poligonos;
UPDATE public.osm_poligonos SET geom=ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)) WHERE NOT ST_IsValid(geom);
ALTER TABLE reparaciones ADD COLUMN invalidas_despues bigint;
ALTER TABLE reparaciones ADD COLUMN vacias_despues bigint;
UPDATE reparaciones SET invalidas_despues=(SELECT count(*) FROM public.osm_poligonos WHERE NOT ST_IsValid(geom)),
 vacias_despues=(SELECT count(*) FROM public.osm_poligonos WHERE ST_IsEmpty(geom));
CREATE TABLE comunas AS SELECT c.cut_com::text id,c.comuna::text nombre,
 c.geom::geometry(MultiPolygon,5361) geom, ST_Area(c.geom)/1e6 area_total_km2,
 ST_Area(ST_Intersection(c.geom,z.geom))/1e6 area_estudio_km2
 FROM public.comunas_cl c CROSS JOIN zona z WHERE ST_Intersects(c.geom,z.geom) AND ST_Area(ST_Intersection(c.geom,z.geom))>0;
CREATE TABLE comunas_sub AS SELECT c.id,s.geom FROM comunas c CROSS JOIN LATERAL ST_Subdivide(c.geom,128) s(geom);
CREATE TABLE calles AS SELECT id, name nombre, highway,
 ST_Intersection(o.geom,z.geom) geom FROM public.osm_lineas o CROSS JOIN zona z
 WHERE highway IS NOT NULL AND ST_Intersects(o.geom,z.geom);
CREATE TABLE edificios AS SELECT o.id,ST_Intersection(o.geom,z.geom) geom,
 ST_PointOnSurface(o.geom)::geometry(Point,5361) punto
 FROM public.osm_poligonos o CROSS JOIN zona z WHERE building IS NOT NULL AND building<>'no'
 AND NOT ST_IsEmpty(o.geom) AND ST_Covers(z.geom,ST_PointOnSurface(o.geom));
ALTER TABLE edificios ADD COLUMN comuna_id text;
UPDATE edificios e SET comuna_id=(SELECT c.id FROM comunas c WHERE ST_Covers(c.geom,e.punto) ORDER BY c.id LIMIT 1);
CREATE TABLE paraderos_osm AS SELECT id,name nombre,o.geom::geometry(Point,5361) geom FROM public.osm_puntos o CROSS JOIN zona z
 WHERE highway='bus_stop' AND ST_Covers(z.geom,o.geom);
CREATE TABLE amenidades AS
 SELECT 'node/'||id id,name nombre,other_tags->'amenity' amenity,o.geom::geometry(Point,5361) geom
 FROM public.osm_puntos o CROSS JOIN zona z WHERE other_tags->'amenity' IS NOT NULL AND ST_Covers(z.geom,o.geom)
 UNION ALL
 SELECT 'area/'||id,name,amenity,ST_PointOnSurface(o.geom)::geometry(Point,5361)
 FROM public.osm_poligonos o CROSS JOIN zona z WHERE amenity IS NOT NULL AND NOT ST_IsEmpty(o.geom) AND ST_Covers(z.geom,ST_PointOnSurface(o.geom));
CREATE TABLE salud AS SELECT * FROM amenidades WHERE amenity IN ('pharmacy','hospital','clinic','doctors');
CREATE TABLE paraderos_gtfs AS SELECT stop_id,stop_name,
 ST_Transform(ST_SetSRID(ST_MakePoint(stop_lon::float8,stop_lat::float8),4326),5361)::geometry(Point,5361) geom
 FROM public.gtfs_stops WHERE stop_lon::float8 BETWEEN -70.75 AND -70.52 AND stop_lat::float8 BETWEEN -33.52 AND -33.36;
CREATE TABLE shapes_completos AS SELECT shape_id,
 ST_MakeLine(ST_Transform(ST_SetSRID(ST_MakePoint(shape_pt_lon::float8,shape_pt_lat::float8),4326),5361) ORDER BY shape_pt_sequence::integer)::geometry(LineString,5361) geom
 FROM public.gtfs_shapes GROUP BY shape_id HAVING count(*)>=2;
CREATE TABLE recorridos AS SELECT s.shape_id,ST_Intersection(s.geom,z.geom) geom
 FROM shapes_completos s CROSS JOIN zona z WHERE ST_Intersects(s.geom,z.geom)
 AND ST_Length(ST_Intersection(s.geom,z.geom))>0
 AND EXISTS(SELECT 1 FROM public.gtfs_trips t WHERE t.shape_id=s.shape_id);
ALTER TABLE reparaciones ADD COLUMN shapes_sin_viaje_en_zona bigint;
UPDATE reparaciones SET shapes_sin_viaje_en_zona=(SELECT count(*) FROM shapes_completos s CROSS JOIN zona z
 WHERE ST_Intersects(s.geom,z.geom) AND ST_Length(ST_Intersection(s.geom,z.geom))>0
 AND NOT EXISTS(SELECT 1 FROM public.gtfs_trips t WHERE t.shape_id=s.shape_id));
CREATE TABLE shape_ruta AS SELECT DISTINCT t.shape_id,t.route_id,r.route_short_name
 FROM public.gtfs_trips t JOIN public.gtfs_routes r USING(route_id) JOIN recorridos s USING(shape_id);
CREATE TABLE ruta_paradero AS SELECT DISTINCT t.route_id,t.trip_id,s.stop_id
 FROM public.gtfs_trips t JOIN public.gtfs_stop_times s USING(trip_id) JOIN paraderos_gtfs p USING(stop_id);
CREATE TABLE ruta_elegida AS SELECT r.route_id,r.route_short_name,count(DISTINCT p.stop_id) paraderos
 FROM public.gtfs_routes r JOIN ruta_paradero p USING(route_id)
 GROUP BY r.route_id,r.route_short_name ORDER BY paraderos DESC,r.route_id LIMIT 1;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['zona','comunas','comunas_sub','calles','edificios','paraderos_osm','amenidades','salud','paraderos_gtfs','shapes_completos','recorridos'] LOOP
 EXECUTE format('CREATE INDEX %I ON analisis.%I USING gist(geom)', 'idx_'||t||'_geom',t);
 EXECUTE format('ANALYZE analisis.%I',t);
 END LOOP;
END $$;
CREATE INDEX idx_edificios_punto ON edificios USING gist(punto);
CREATE INDEX idx_edificios_comuna ON edificios(comuna_id);
CREATE INDEX idx_shape_ruta_shape ON shape_ruta(shape_id);
CREATE INDEX idx_ruta_paradero_ruta ON ruta_paradero(route_id);
ANALYZE;
