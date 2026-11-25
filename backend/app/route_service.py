"""把数据库中的图交给算法，并组装可供前端使用的结果。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Attraction, Road
from backend.app.routing import Edge, shortest_path
from backend.app.schemas import Place, RouteSegment, ShortestRoute


def plan_route(session: Session, start: int, end: int) -> ShortestRoute | None:
    places = {row.id: Place.model_validate(row, from_attributes=True)
              for row in session.scalars(select(Attraction).order_by(Attraction.id))}
    if start not in places or end not in places:
        raise KeyError('起点或终点不存在')
    roads = [Edge(row.id, row.start_id, row.end_id, row.distance_m, row.bidirectional)
             for row in session.scalars(select(Road).order_by(Road.id))]
    result = shortest_path(set(places), roads, start, end)
    if result is None:
        return None
    return ShortestRoute(
        start_id=start, end_id=end, distance_m=result.distance_m,
        path=[places[node] for node in result.node_ids],
        segments=[RouteSegment(road_id=edge.road_id, start_id=a, end_id=b,
                               distance_m=edge.distance_m)
                  for a, b, edge in zip(result.node_ids, result.node_ids[1:], result.edges)],
    )
