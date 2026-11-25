import json
from math import inf

import pytest

from backend.app.repository import DATA_FILE
from backend.app.routing import Edge, shortest_path


def test_demo_all_pairs_against_floyd_warshall():
    # Floyd-Warshall 独立计算全图距离，不复用 Dijkstra 的堆与前驱逻辑。
    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    nodes = {p['id'] for p in data['places']}
    edges = [Edge(r['id'], r['start_id'], r['end_id'], r['distance_m']) for r in data['roads']]
    distances = {(a, b): 0 if a == b else inf for a in nodes for b in nodes}
    for edge in edges:
        distances[edge.start_id, edge.end_id] = edge.distance_m
        distances[edge.end_id, edge.start_id] = edge.distance_m
    for k in nodes:
        for a in nodes:
            for b in nodes:
                distances[a, b] = min(distances[a, b], distances[a, k] + distances[k, b])
    for a in nodes:
        for b in nodes:
            result = shortest_path(nodes, edges, a, b)
            assert result is not None
            assert result.distance_m == distances[a, b]
            assert result.node_ids[0] == a and result.node_ids[-1] == b
            assert len(result.edges) == len(result.node_ids) - 1
            assert sum(edge.distance_m for edge in result.edges) == result.distance_m
            for left, right, edge in zip(result.node_ids, result.node_ids[1:], result.edges):
                assert {left, right} == {edge.start_id, edge.end_id}


def test_shorter_detour_and_old_queue_entries():
    edges = [Edge(0, 0, 1, 10), Edge(1, 0, 2, 1), Edge(2, 2, 1, 1), Edge(3, 1, 3, 20)]
    result = shortest_path({0, 1, 2, 3}, edges, 0, 3)
    assert result.node_ids == [0, 2, 1, 3]
    assert result.distance_m == 22


def test_disconnected_same_node_and_one_way():
    edges = [Edge(0, 0, 1, 10, False)]
    assert shortest_path({0, 1, 2}, edges, 0, 2) is None
    assert shortest_path({0, 1, 2}, edges, 1, 0) is None
    assert shortest_path({0, 1, 2}, edges, 0, 1).distance_m == 10
    result = shortest_path({0, 1, 2}, edges, 2, 2)
    assert result.node_ids == [2] and result.edges == [] and result.distance_m == 0


@pytest.mark.parametrize('edge', [Edge(0, 0, 1, -1), Edge(0, 0, 1, 0), Edge(0, 0, 9, 1)])
def test_reject_invalid_graph(edge):
    with pytest.raises(ValueError):
        shortest_path({0, 1}, [edge], 0, 1)


def test_unknown_node():
    with pytest.raises(KeyError):
        shortest_path({0}, [], 0, 99)
