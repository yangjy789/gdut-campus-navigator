"""Extract this project's C initializer; this is not a general C parser.

Run from any directory: python scripts/prepare_demo.py
Only the Python standard library is required.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract(source):
    arrays = {}
    for key in ("codes", "names", "notes"):
        match = re.search(rf'char\s*\*{key}\[MAXV\]\s*=\s*\{{(.*?)\}};', source, re.S)
        if not match:
            raise ValueError(f"Missing C array: {key}")
        arrays[key] = re.findall(r'"([^"\n]*)"', match[1])
    count = int(re.search(r'#define\s+MAXV\s+(\d+)', source)[1])
    if any(len(values) != count for values in arrays.values()):
        raise ValueError("C array length differs from MAXV")
    places = [dict(id=i, code=code, name=name, description=note,
                   latitude=None, longitude=None, verification_status="demo_only")
              for i, (code, name, note) in enumerate(zip(
                  arrays['codes'], arrays['names'], arrays['notes']))]
    roads = [dict(id=i, start_id=int(a), end_id=int(b), distance_m=int(d),
                  bidirectional=True, verification_status="demo_only")
             for i, (a, b, d) in enumerate(re.findall(
                 r'AddRoad\(G,\s*(\d+),\s*(\d+),\s*(\d+)\)', source))]
    return dict(dataset_type="course_demo", coordinate_system=None,
                warning="Not verified GDUT campus locations or distances.",
                places=places, roads=roads)


def validate(data):
    places, roads = data['places'], data['roads']
    ids = {p['id'] for p in places}
    if not places or len(ids) != len(places):
        raise ValueError("Empty or duplicate place IDs")
    if len({p['code'] for p in places}) != len(places):
        raise ValueError("Duplicate place codes")
    edges, neighbors = set(), {i: set() for i in ids}
    for road in roads:
        a, b = road['start_id'], road['end_id']
        if a not in ids or b not in ids or a == b:
            raise ValueError("Invalid road endpoints")
        if road['distance_m'] <= 0:
            raise ValueError("Road distance must be positive")
        pair = tuple(sorted((a, b)))
        if pair in edges:
            raise ValueError("Duplicate undirected road")
        edges.add(pair)
        neighbors[a].add(b)
        neighbors[b].add(a)
    reached, pending = set(), [places[0]['id']]
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(neighbors[current] - reached)
    if reached != ids:
        raise ValueError("Graph is disconnected")
    return dict(place_count=len(places), road_count=len(roads),
                connected=True, real_navigation_ready=False)


def main():
    raw = (ROOT / 'legacy/campus_guide.c').read_bytes()
    data = extract(raw.decode('utf-8-sig'))
    report = validate(data)
    report['source_sha256'] = hashlib.sha256(raw).hexdigest()
    report['checks'] = ['unique IDs and codes', 'valid endpoints',
                        'positive distances', 'no duplicate roads', 'connected graph']
    for path, content in [('data/demo/campus.json', data),
                          ('docs/stage-0-check.json', report)]:
        (ROOT / path).write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
