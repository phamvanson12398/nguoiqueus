"""Pack Natural Earth GeoJSON (public domain, naturalearthdata.com) into small JSON files for core/maps.py.
    python tools/ne_pack.py <dir with ne_50m_*.geojson>
-> data/geo/{land,lakes,rivers}.json : {"items": [{"b": [minlon,minlat,maxlon,maxlat], "c": [[lon,lat],...], "n": name}]}"""
import json, os, sys
src = sys.argv[1]; out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "geo")
os.makedirs(out, exist_ok=True)

def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon": return [c[0]]
    if t == "MultiPolygon": return [p[0] for p in c]
    if t == "LineString": return [c]
    if t == "MultiLineString": return c
    return []

for name, f in (("land", "ne_50m_land"), ("lakes", "ne_50m_lakes"), ("rivers", "ne_50m_rivers_lake_centerlines")):
    g = json.load(open(os.path.join(src, f + ".geojson"), encoding="utf-8"))
    items = []
    for ft in g["features"]:
        nm = (ft.get("properties") or {}).get("name") or ""
        for r in rings(ft["geometry"]):
            pts = []
            for lon, lat, *_ in r:
                p = [round(lon, 2), round(lat, 2)]
                if not pts or p != pts[-1]: pts.append(p)
            if len(pts) < 2: continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            items.append({"b": [min(xs), min(ys), max(xs), max(ys)], "c": pts, "n": nm})
    json.dump({"source": "Natural Earth 1:50m (public domain)", "items": items}, open(os.path.join(out, name + ".json"), "w"), separators=(",", ":"))
    print(name, len(items), os.path.getsize(os.path.join(out, name + ".json")))
