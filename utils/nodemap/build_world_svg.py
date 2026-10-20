"""Build website/network/nodes/world.svg from Natural Earth 1:110m admin-0 countries (public domain).

Development-time only:  python3 -I utils/nodemap/build_world_svg.py ne_110m_admin_0_countries.geojson website/network/nodes/world.svg
Each country is one <path> with data-cc set to its ISO 3166-1 alpha-2 code (ISO_A2_EH, which
also covers France and Norway). Equirectangular projection, Antarctica left out.
"""
import json, sys
from xml.sax.saxutils import quoteattr

WIDTH, NORTH, SOUTH = 1000, 84.0, -58.0
SCALE = WIDTH / 360.0
HEIGHT = round((NORTH - SOUTH) * SCALE)
# Areas Natural Earth lists without an ISO code are drawn as part of the country that ISO assigns them to.
MERGE = {"N. Cyprus": "CY", "Somaliland": "SO"}


def point(lon, lat):
    lat = max(SOUTH, min(NORTH, lat))
    return f"{(lon + 180) * SCALE:.1f} {(NORTH - lat) * SCALE:.1f}"


def ring(coords):
    return "M" + "L".join(point(lon, lat) for lon, lat in coords) + "Z"


def main(source, target):
    features = json.load(open(source, encoding="utf-8"))["features"]
    shapes = {}
    for feature in features:
        props = feature["properties"]
        code = MERGE.get(props["NAME"], props["ISO_A2_EH"])
        if code == "AQ" or len(code) != 2 or not code.isalpha():
            continue
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        entry = shapes.setdefault(code, {"name": props["NAME"], "d": []})
        if props["NAME"] not in MERGE:
            entry["name"] = props["NAME"]
        entry["d"].extend(ring(r) for polygon in polygons for r in polygon)
    with open(target, "w", encoding="utf-8") as out:
        out.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="world-title">'
                  f'<title id="world-title">World map by country</title>\n')
        for code in sorted(shapes):
            out.write(f'<path data-cc="{code}" data-name={quoteattr(shapes[code]["name"])} d="{"".join(shapes[code]["d"])}"/>\n')
        out.write("</svg>\n")
    print(f"{len(shapes)} countries written to {target}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
