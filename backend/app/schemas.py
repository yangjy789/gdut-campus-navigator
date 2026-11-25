"""接口返回的数据结构，同时用于校验 JSON 数据。"""
from typing import Literal

from pydantic import BaseModel, Field


class Place(BaseModel):
    id: int = Field(ge=0)
    code: str
    name: str
    description: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    verification_status: Literal['demo_only']


class PlaceList(BaseModel):
    dataset_type: Literal['course_demo'] = 'course_demo'
    real_navigation_ready: bool = False
    total: int
    items: list[Place]


class RouteSegment(BaseModel):
    road_id: int
    start_id: int
    end_id: int
    distance_m: int = Field(gt=0)


class ShortestRoute(BaseModel):
    dataset_type: Literal['course_demo'] = 'course_demo'
    real_navigation_ready: bool = False
    algorithm: Literal['dijkstra'] = 'dijkstra'
    start_id: int
    end_id: int
    distance_m: int = Field(ge=0)
    path: list[Place]
    segments: list[RouteSegment]


class RoadInfo(BaseModel):
    id: int
    start_id: int
    end_id: int
    distance_m: int
    bidirectional: bool


class RoadList(BaseModel):
    dataset_type: Literal['course_demo'] = 'course_demo'
    real_navigation_ready: bool = False
    total: int
    items: list[RoadInfo]
