FROM postgis/postgis:16-3.5-alpine
RUN apk add --no-cache gdal-tools gdal-driver-pg python3 py3-psycopg2 py3-matplotlib py3-reportlab
