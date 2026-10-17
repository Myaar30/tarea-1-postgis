# Inventario medido

| Tabla | Filas |
|---|---:|
| amenidades | 20875 |
| calles | 100915 |
| cobertura_edificios | 118950 |
| comunas | 30 |
| comunas_sub | 182 |
| edificios | 118950 |
| gtfs_routes | 428 |
| gtfs_shapes | 456573 |
| gtfs_stop_times | 1098529 |
| gtfs_stops | 18455 |
| gtfs_trips | 26159 |
| hexagonos | 636 |
| mv_grilla | 636 |
| paraderos_gtfs | 7162 |
| paraderos_osm | 6572 |
| recorridos | 708 |
| reparaciones | 1 |
| ruta_elegida | 1 |
| ruta_paradero | 694037 |
| salud | 1355 |
| shape_ruta | 708 |
| shapes_completos | 981 |
| zona | 1 |

## Índices

- `amenidades.idx_amenidades_geom`: `CREATE INDEX idx_amenidades_geom ON analisis.amenidades USING gist (geom)`
- `calles.idx_calles_geom`: `CREATE INDEX idx_calles_geom ON analisis.calles USING gist (geom)`
- `cobertura_edificios.idx_cobertura_geom`: `CREATE INDEX idx_cobertura_geom ON analisis.cobertura_edificios USING gist (geom)`
- `comunas.idx_comunas_geom`: `CREATE INDEX idx_comunas_geom ON analisis.comunas USING gist (geom)`
- `comunas_sub.idx_comunas_sub_geom`: `CREATE INDEX idx_comunas_sub_geom ON analisis.comunas_sub USING gist (geom)`
- `edificios.idx_edificios_comuna`: `CREATE INDEX idx_edificios_comuna ON analisis.edificios USING btree (comuna_id)`
- `edificios.idx_edificios_geom`: `CREATE INDEX idx_edificios_geom ON analisis.edificios USING gist (geom)`
- `edificios.idx_edificios_punto`: `CREATE INDEX idx_edificios_punto ON analisis.edificios USING gist (punto)`
- `hexagonos.hexagonos_pkey`: `CREATE UNIQUE INDEX hexagonos_pkey ON analisis.hexagonos USING btree (i, j)`
- `hexagonos.idx_hexagonos_geom`: `CREATE INDEX idx_hexagonos_geom ON analisis.hexagonos USING gist (geom)`
- `mv_grilla.idx_mv_grilla_geom`: `CREATE INDEX idx_mv_grilla_geom ON analisis.mv_grilla USING gist (geom)`
- `paraderos_gtfs.idx_paraderos_gtfs_geom`: `CREATE INDEX idx_paraderos_gtfs_geom ON analisis.paraderos_gtfs USING gist (geom)`
- `paraderos_osm.idx_paraderos_osm_geom`: `CREATE INDEX idx_paraderos_osm_geom ON analisis.paraderos_osm USING gist (geom)`
- `recorridos.idx_recorridos_geom`: `CREATE INDEX idx_recorridos_geom ON analisis.recorridos USING gist (geom)`
- `ruta_paradero.idx_ruta_paradero_ruta`: `CREATE INDEX idx_ruta_paradero_ruta ON analisis.ruta_paradero USING btree (route_id)`
- `salud.idx_salud_geom`: `CREATE INDEX idx_salud_geom ON analisis.salud USING gist (geom)`
- `shape_ruta.idx_shape_ruta_shape`: `CREATE INDEX idx_shape_ruta_shape ON analisis.shape_ruta USING btree (shape_id)`
- `shapes_completos.idx_shapes_completos_geom`: `CREATE INDEX idx_shapes_completos_geom ON analisis.shapes_completos USING gist (geom)`
- `zona.idx_zona_geom`: `CREATE INDEX idx_zona_geom ON analisis.zona USING gist (geom)`

## Reparaciones

[{"tabla": "osm_poligonos", "invalidas_antes": 368, "vacias_antes": 0, "invalidas_despues": 0, "vacias_despues": 309, "shapes_sin_viaje_en_zona": 101}]

Edificios sin comuna: 0. Diferencia Q4: 4.092726157978177e-12 km.