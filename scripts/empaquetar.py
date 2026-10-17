"""Crea el ZIP de entrega con resultados, sin archivos fuente ni temporales."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
target=root.parent/'Entrega_PostGIS_Galaz_Yanez_Roa.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':continue
        rel=path.relative_to(root)
        if rel.parts[0]=='datos' and path.name!='.gitkeep':continue
        if rel.parts[0]=='datos_fuente' and path.name not in ('.gitkeep','fuentes.json'):continue
        z.write(path,Path('entrega')/rel)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert not any(n.endswith(('.pbf','.gpkg','.shp')) for n in z.namelist())
print(target)
