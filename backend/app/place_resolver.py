"""把用户或模型给出的地点短语解析为数据库里的真实地点编号。

中文别名与前端 demo-layout.ts 的 labels 保持一致；管理员改名时以原始英文示例名匹配。
解析失败或存在歧义时返回 None，由调用方明确提示用户，绝不猜测地点。
"""
from backend.app.schemas import Place

# code -> 中文别名（与前端展示别名一致）
CODE_ALIASES: dict[str, tuple[str, ...]] = {
    'NG': ('北门', '北门入口'),
    'SG': ('南门', '南门入口'),
    'LIB': ('图书馆',),
    'TA': ('教学楼A', '教学楼 A', 'A教学楼'),
    'TB': ('教学楼B', '教学楼 B', 'B教学楼'),
    'LAB': ('实验楼',),
    'SC': ('学生活动中心', '活动中心'),
    'DIN': ('食堂', '饭堂'),
    'DOR': ('宿舍区', '宿舍'),
    'SP': ('运动场', '操场'),
    'ADM': ('行政楼',),
    'LAK': ('湖畔花园', '湖畔'),
}

# 原始英文示例名，仅当数据库名称仍是示例名时用于匹配。
ORIGINAL_NAMES: dict[str, str] = {
    'NG': 'NorthGate', 'LIB': 'Library', 'TA': 'TeachingA', 'TB': 'TeachingB',
    'LAB': 'LabBuilding', 'SC': 'StudentCenter', 'DIN': 'DiningHall',
    'DOR': 'Dormitory', 'SP': 'SportsField', 'ADM': 'Administration',
    'SG': 'SouthGate', 'LAK': 'LakeGarden',
}


def _normalized(text: str) -> str:
    return ''.join(text.lower().split())


def aliases_for(place: Place) -> set[str]:
    """列出一个地点所有可接受的别名形式（已归一化，去空格、小写）。"""
    result = {_normalized(place.code), _normalized(place.name)}
    original = ORIGINAL_NAMES.get(place.code)
    if original and place.name == original:
        result.update(_normalized(a) for a in CODE_ALIASES.get(place.code, ()))
    return result


def resolve_place(expr: str, places: list[Place]) -> int | None:
    """完整名称或别名唯一命中才接受，保留有限问路前缀兼容。"""
    text = _normalized(expr)
    if not text:
        return None

    # 只允许完整地点名称/别名与有限语法前缀，不把附近设施或多个地点猜成一个。
    # 名称本身可能重复，必须汇总所有精确命中后再判断唯一性。
    forms = {text}
    for prefix in ('从', '到', '去', '前往'):
        if text.startswith(prefix):
            forms.add(text[len(prefix):])
    candidates = {p.id for p in places if forms & aliases_for(p)}
    return next(iter(candidates)) if len(candidates) == 1 else None


def place_names(places: list[Place]) -> list[str]:
    """用于向用户展示「可识别的地点」提示。"""
    return [CODE_ALIASES[p.code][0] if ORIGINAL_NAMES.get(p.code) == p.name
            else p.name for p in places]
