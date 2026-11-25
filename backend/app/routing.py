"""不依赖 FastAPI 或数据库的最短路径算法。"""
from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf


@dataclass(frozen=True)
class Edge:
    road_id: int
    start_id: int
    end_id: int
    distance_m: int
    bidirectional: bool = True


@dataclass(frozen=True)
class PathResult:
    node_ids: list[int]
    edges: list[Edge]
    distance_m: int


def shortest_path(node_ids: set[int], edges: list[Edge], start: int, end: int) -> PathResult | None:
    if start not in node_ids or end not in node_ids:
        raise KeyError('起点或终点不存在')
    graph: dict[int, list[tuple[int, Edge]]] = {node: [] for node in node_ids}
    for edge in edges:
        if edge.distance_m <= 0 or edge.start_id not in graph or edge.end_id not in graph:
            raise ValueError('道路数据包含非法距离或端点')
        graph[edge.start_id].append((edge.end_id, edge))
        if edge.bidirectional:
            graph[edge.end_id].append((edge.start_id, edge))

    distances = {start: 0}
    previous: dict[int, tuple[int, Edge]] = {}
    queue = [(0, start)]
    while queue:
        distance, node = heappop(queue)
        # 更短的候选可能已加入队列，旧候选无需再次处理。
        if distance != distances[node]:
            continue
        if node == end:
            break
        for neighbor, edge in graph[node]:
            candidate = distance + edge.distance_m
            if candidate < distances.get(neighbor, inf):
                distances[neighbor] = candidate
                previous[neighbor] = (node, edge)
                heappush(queue, (candidate, neighbor))
    if end not in distances:
        return None

    nodes, path_edges = [end], []
    while nodes[-1] != start:
        parent, edge = previous[nodes[-1]]
        nodes.append(parent)
        path_edges.append(edge)
    return PathResult(list(reversed(nodes)), list(reversed(path_edges)), distances[end])
