# Tarea 1 - PostGIS de punta a punta: Santiago centro

**Integrantes:** Nicolas Galaz, Martin Yañez y Eduardo Roa.  
ELE051-B / EIN102B · USM 2026-2 · Paralelo 701.

## Reproducir desde cero

Requisitos: Docker Desktop encendido, Docker Compose y Python 3 en el equipo.
Se recomienda disponer de 8 GB de RAM y 8 GB libres. No hace falta instalar
PostGIS, GDAL, bibliotecas de Python ni Jupyter en el equipo: vienen en la imagen.

1. Descargar los tres archivos de la tabla siguiente en `datos_fuente/`.
2. Abrir una terminal **en esta carpeta `entrega`**.
3. Ejecutar:

```text
docker compose up -d --build
python cargar.py
```

En Linux/macOS puede ser `python3 cargar.py`. El script espera a que la base
responda y ejecuta todo el proceso: recorte OSM, carga de tres fuentes, ETL,
índices, estadísticas, siete consultas, planes, exportaciones, mapas e informe.
No se ejecutan los notebooks ni se necesita editar rutas. También puede
ejecutarse directamente dentro del contenedor:

```text
docker compose exec -T db python3 /trabajo/scripts/pipeline.py
```

Una vez calculadas las tablas y los resultados, `python cargar.py --solo-salidas`
permite regenerar las exportaciones, ejecutar los controles y reconstruir mapas
e informe sin volver a descargar ni procesar las fuentes. Es opcional; la
ejecución normal sin argumentos hace todo.

El proceso reemplaza sus propias tablas y salidas al repetirse. No modifica
los laboratorios originales. `docker compose down` apaga el entorno y conserva
la base en el volumen con nombre `tarea1-santiago_tarea1-pgdata`.
El acceso opcional desde otro cliente es localhost:5434, base/usuario
`tarea1`/`postgres`, clave local `tarea1local`.

## Fuentes y fechas reales de esta ejecución

| Archivo en datos_fuente | Fuente / versión | Descarga |
|---|---|---|
| `chile-latest.osm.pbf` | [Geofabrik / OSM](https://download.geofabrik.de/south-america/chile-latest.osm.pbf), datos hasta 2026-10-14T20:21:12Z | 2026-10-15 |
| `GTFS_20261003.zip` | [DTPM](https://www.dtpm.cl/descargas/gtfs/GTFS_20261003.zip), feed V168.20261003, vigencia 03-10 a 31-12-2026 | 2026-10-15 |
| `DPA_2023.zip` | [IDE Chile, DPA 2023](https://www.geoportal.cl/geoportal/catalog/download/912598ad-ac92-35f6-8045-098f214bd9c2), miembros COMUNAS_v1 | 2026-10-15 |

La página para verificar el GTFS es [GTFS vigente](https://www.dtpm.cl/index.php/noticias/gtfs-vigente).
Guardar sólo un `GTFS*.zip` en la carpeta. Los ZIP no se descomprimen a mano.
OSM: © OpenStreetMap contributors, licencia ODbL. DPA: IDE Chile / CC-BY según
la fuente docente. GTFS: DTPM / Red Metropolitana; se preserva su atribución.

`resultados/fuentes.json` conserva los nombres, fechas, tamaños y SHA-256
del material procesado. Si se cambia una fuente, actualizar previamente
`datos_fuente/fuentes.json`. Nunca inferir su versión desde el día de ejecución.
Se usa el GTFS vigente al descargar; no se presenta como el utilizado en septiembre.

## Archivos de la entrega

- `Dockerfile`, `docker-compose.yml`, `cargar.py`: infraestructura y entrada única.
- `scripts/pipeline.py`: carga con GDAL y COPY por flujo, consultas y verificaciones.
- `sql/01_etl.sql`: geometrías en 5361, capas propias, reparación e índices.
- `sql/02_consultas.sql`: las seis preguntas obligatorias y la propia.
- `scripts/informe.py`: genera dos mapas y un PDF de hasta seis páginas.
- `INVENTARIO.md`: tablas, conteos, índices y reparación **medidos**.
- `resultados/q1.csv` ... `q7.csv`: resultados completos, sin truncar.
- `resultados/*_plan.json`: EXPLAIN ANALYZE, BUFFERS y cuatro mediciones por consulta.
- `resultados/uso_indices.csv`, `versiones.txt`: evidencia del entorno y uso de índices.
- `resultados/verificacion.json`: 14 comprobaciones de geometrías, conteos,
  asignación única, pertenencia a rutas y equivalencia de kilómetros.
- `resultados/mv_grilla.geojson`, `comunas.geojson`, `cobertura_edificios.geojson`:
  resultados exportados en EPSG:4326, conservados para revisar los mapas.
- `resultados/mapa_grilla.png`, `mapa_cobertura.png`, `Informe_Tarea1_PostGIS.pdf`.
- `resultados/Informe_Tarea1_PostGIS_editable.docx`: mismo informe en Word,
  con texto y tablas editables y mapas como imágenes. Si cambian los resultados,
  se puede regenerar con `scripts/crear_editable.py` (requiere python-docx y
  reportlab en el Python que lo ejecute); no es necesario para la carga normal.

El `.gitignore` excluye los archivos fuente y los datos intermedios. Las salidas
analíticas y los mapas sí deben acompañar la entrega. No se realiza publicación
en GitHub por instrucción del equipo.

## Decisiones que condicionan las respuestas

La caja es exactamente lon [-70.75,-70.52], lat [-33.52,-33.36]. Todas las capas
de trabajo se transforman a EPSG:5361. Las distancias son en línea recta.
La DPA se carga desde su shapefile oficial en lugar del SQL del Lab 03 porque
ese SQL no venía en la carpeta recibida; GDAL aplica la misma transformación
5360 a 5361. La caja se densifica en grados antes de reproyectar para preservar
sus bordes curvos en UTM; usar sólo cuatro esquinas excluía dos paraderos a
menos de 3 m del borde proyectado. El DPA incluye 345 comunas del país; el análisis retiene las que
intersectan la caja con área positiva.

OSM se convierte con GDAL como en el Lab 05. Se cuenta la invalidez antes y
después de reparar con ST_MakeValid, ST_CollectionExtract y ST_Multi, conservando
el resultado en `analisis.reparaciones`. Se excluyen polígonos vacíos. Los
edificios se asignan por punto interior, con desempate por código comunal;
no se multiplica un edificio que toca dos comunas. Los objetos etiquetados
como building=no se excluyen.

Las cinco tablas GTFS se cargan con COPY, por flujo desde el ZIP; stop_times
permite asociar paraderos reales a una ruta. Se construye una LineString por
shape_id con secuencia numérica completa **antes** de recortar su geometría.
Se excluyen del análisis los shapes que no tienen viajes asociados en trips
(se registra cuántos en analisis.reparaciones).
El recorte puede producir MultiLineString sin alterar la LineString original
en `shapes_completos`. La relación muchos-a-muchos `shape_ruta` conserva las
variantes, sin multiplicar longitudes por viajes. No se pondera por frecuencia.

Q1 informa densidad por área comunal completa, y además por área observada
para hacer explícito el sesgo de comunas parcialmente recortadas. Q2 compara
las mismas huellas OSM con ambas fuentes de paraderos. Se usa ST_DWithin <=500 m;
Q3 considera pareja a <=50 m. Todos los paraderos se limitan a la caja, como
pide el enunciado: puede haber efecto de borde.

Q4 suma shapes distintos, no kilómetros únicos de calles. Se comparan cuatro
ejecuciones de cada estrategia, informando la primera y la mediana de las tres
restantes; no se fuerza un plan. Se exige coincidencia de longitudes con
tolerancia de 1 m por comuna. La unión por comuna/shape evita contar dos veces
segmentos que caigan en un límite de ST_Subdivide.

Q5 elige la ruta con más paraderos distintos en la caja y usa LATERAL + KNN.
Ante servicios equidistantes cualquiera de los más próximos es válido.
La grilla usa **lado** 500 m, cuenta edificios por punto interior con asignación
única y rutas por route_id distinto. El criterio explícito del top 10 es
`edificios/(1+rutas)`, con desempates publicados en SQL. Las celdas de borde
son parciales. La pregunta propia Q7 mide diversidad funcional de usos OSM
en los entornos de 300 m de cada paradero GTFS mediante entropía de Shannon
(-sum(p*ln(p))), cantidad de categorías y amenidades. No es una tasa de cobertura:
caracteriza mezcla y equilibrio de funciones urbanas. Una amenidad puede
caracterizar varios entornos; los totales por paradero no se suman como objetos únicos.

GiST cubre las geometrías de todas las tablas derivadas; edificios tiene también
un GiST en punto. B-tree cubre enlaces y se ejecuta ANALYZE. Los índices
efectivamente usados figuran en los planes; los no usados se registran mediante
pg_stat_user_indexes. Cero lecturas en una ejecución no demuestra inutilidad
permanente, por lo que no se eliminan automáticamente.

## Dificultades y límites

La imagen Debian inicial falló por repositorios/paquetes retirados (HTTP 404).
Se resolvió usando la variante Alpine del Lab 05 con herramientas declaradas.
La DPA usa el nombre COMUNAS_v1, admitido por el cargador. Al repetir las exportaciones, el driver
GeoJSON no admite DeleteLayer: se reemplaza explícitamente cada archivo de
salida propio antes de exportarlo de nuevo. No se sustituyen
fuentes reales por datos sintéticos. Los planes y tiempos dependen del equipo
y caché; no se atribuye una mejora a ST_Subdivide sin medirla.

OSM muestra lo cartografiado, GTFS lo declarado por el operador. Ninguna de
estas fuentes demuestra por sí sola demanda, accesibilidad peatonal efectiva,
calidad del servicio o población beneficiada. El informe limita sus conclusiones
a la fecha, dominio espacial y objetos efectivamente observados.
