"""整理学校 2026 年官方地图中的事实；像素点只用于图上定位，绝不是经纬度。"""
import hashlib
import json
import shutil
from pathlib import Path

from backend.app.config import ROOT

ARTICLE = 'https://www.gdut.edu.cn/info/1715/23413.htm'
PDF = ('https://www.gdut.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl'
       '&owner=1674704880&wbfileid=BC27A786C34B9D3D6D9BE95D1DBBA179')
SOURCE = ROOT / 'data/real/sources'
OUTPUT = ROOT / 'data/public_campus'

# 根据 PDF 第 1 页可见建筑名称与标签逐项整理。x/y 为 1317×2000 渲染图的近似符号中心。
# 没有道路测量值，不导入任何距离或通行边。规划建筑单列，禁止混作已建建筑。
ROWS = [
    ('south-gate','南门','教学区','出入口',593,1153,[],False),
    ('east-gate','东门','教学区','出入口',1204,1025,[],False),
    ('teaching-west-gate','教学区西北门','教学区','出入口',495,465,[],False),
    ('library','图书馆','教学区','学习',780,886,[],False),
    ('history','校史馆','教学区','文化',705,838,[],False),
    ('administration','行政楼','教学区','服务',653,1073,[],False),
    ('comprehensive','综合楼','教学区','服务',658,1030,[],False),
    ('conference','会议中心','教学区','服务',725,1158,[],False),
    ('science','理学馆','教学区','学习',908,1183,[],False),
    ('teaching-1','教学一号楼','教学区','学习',1087,887,[],False),
    ('teaching-2','教学二号楼','教学区','学习',987,843,[],False),
    ('teaching-3','教学三号楼','教学区','学习',891,811,[],False),
    ('teaching-4','教学四号楼','教学区','学习',971,811,[],False),
    ('teaching-5','教学五号楼','教学区','学习',852,782,[],False),
    ('teaching-6','教学六号楼','教学区','学习',893,754,[],False),
    ('engineering-1','工学一号馆','教学区','学习',815,1135,[],False),
    ('engineering-2','工学二号馆','教学区','学习',845,1077,[],False),
    ('engineering-3','工学三号馆','教学区','学习',916,1043,[],False),
    ('engineering-4','工学四号馆','教学区','学习',947,1002,[],False),
    ('experiment-1','实验一号楼','教学区','学习',998,1108,[],False),
    ('experiment-2','实验二号楼','教学区','学习',1045,1071,[],False),
    ('experiment-3','实验三号楼','教学区','学习',1056,1035,[],False),
    ('experiment-4','实验四号楼','教学区','学习',1088,1008,[],False),
    ('qiushi-a','求是科技楼A座','教学区','科研',1167,840,['新科技大楼'],False),
    ('qiushi-b','求是科技楼B座','教学区','科研',1159,799,['新科技大楼'],False),
    ('innovation-a','创新科技楼A座','教学区','科研',1072,780,['科创实训楼'],False),
    ('innovation-b','创新科技楼B座','教学区','科研',996,751,['科创实训楼'],False),
    ('lide-a','立德科技楼A座','教学区','科研',1142,1195,['科技南楼'],False),
    ('lide-b','立德科技楼B座','教学区','科研',1158,1159,['科技北楼'],False),
    ('culture','文化活动中心','教学区','文化',685,662,[],False),
    ('gym','体育馆','教学区','运动',511,541,[],False),
    ('stadium','中心田径场','教学区','运动',595,624,[],False),
    ('cricket','板球场','教学区','运动',252,477,[],False),
    ('tennis','网球场','教学区','运动',396,493,[],False),
    ('university-square','工大广场','教学区','景观',625,1191,['正门广场'],False),
    ('lake','团结湖','教学区','景观',489,1002,['人工湖'],False),
    ('qinfen-square','勤奋广场','教学区','景观',947,931,['创新大道东侧广场'],False),
    ('east-canteen-1','东一食堂','生活东区','生活',1118,500,[],False),
    ('east-canteen-2','东二食堂','生活东区','生活',750,535,[],False),
    ('hospital','医院','生活东区','服务',1040,454,[],False),
    ('east-service','东区服务中心','生活东区','服务',1061,477,[],False),
    ('mental-health','心理健康教育中心','生活东区','服务',961,552,[],False),
    ('east-west-gate','东区西门','生活东区','出入口',746,468,[],False),
    ('east-east-gate','东区东门','生活东区','出入口',1167,568,[],False),
    ('west-canteen-3','西三食堂','生活西区','生活',500,403,[],False),
    ('west-canteen-4','西四食堂','生活西区','生活',250,230,[],False),
    ('west-east-gate','西区东门','生活西区','出入口',594,381,[],False),
    ('west-west-gate','西区西门','生活西区','出入口',200,174,[],False),
    ('west-teacher','西区教师宿舍','生活西区','生活',306,296,[],False),
    ('postdoc','博士后公寓','生活西区','生活',330,255,[],False),
    ('shuren','树人科技楼','教学区','科研',1165,1232,[],True),
]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pdf = SOURCE / 'official-map-2026.pdf'
    image = SOURCE / 'official-map-2026.png'
    if not pdf.read_bytes().startswith(b'%PDF'):
        raise ValueError('原始附件不是 PDF')
    places = [dict(id=key,name=name,region=region,category=category,
                   image_position={'x':x,'y':y},aliases=aliases,planned=planned,
                   latitude=None,longitude=None,verification_status='official_document_only',
                   source_url=ARTICLE,source_document_url=PDF,source_page=1,
                   checked_on='2026-11-23')
              for key,name,region,category,x,y,aliases,planned in ROWS]
    result = dict(dataset_type='official_public_reference',campus='广东工业大学大学城校区',
        real_navigation_ready=False,coordinate_system='official_map_image_pixels',
        map=dict(width=1317,height=2000,image_url='/api/campus/real/map',
                 position_accuracy='manual_approximate_symbol_center'),
        sources=[dict(title='大学城校区新增建筑、景观命名公告',url=ARTICLE,published_on='2026-01-07'),
                 dict(title='附件1：大学城校区地图示意图',url=PDF,page=1,
                      sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())],
        attribution='底图来源：广东工业大学官方地图附件；图文版权归原权利人。',
        limitations=['图上定位为手工标注的近似符号中心，不是经纬度或建筑入口。',
                     '资料已与官网文件核对，未实地核验；没有开放时间及实时通行信息。',
                     '官方示意图没有可直接使用的道路测距，不提供真实路线与距离。'],
        places=places,roads=[])
    (OUTPUT/'campus.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(image, OUTPUT/'official-map.png')
    knowledge_file = ROOT / 'data/knowledge/campus.json'
    knowledge = [d for d in json.loads(knowledge_file.read_text(encoding='utf-8'))
                 if not d['id'].startswith('public-place-')]
    updates = {
        'campus-map': ('学校官网2026年1月7日发布大学城校区新增建筑、景观命名公告，'
            '附件1提供大学城校区地图示意图。2020年的旧平面图入口仍可查阅，'
            '优先参考2026年附件；官方示意图不提供实时通行状态或可直接用于导航的精确道路长度。'),
        'project-demo': ('当前首页默认展示官网真实资料：来自2026年官方地图的51个地点条目，'
            '其中1处树人科技楼在来源中标为规划中。图上标记是近似符号位置，不是经纬度或入口坐标。'
            '课设算路演示是另一模式，仍使用12个示例地点和18条示例道路，示例距离不能用于真实校园导航。'
            '真实资料页尚无可计算的道路网络，不提供真实路线。'),
        'project-search': ('首页官网真实资料模式支持按地点名称、旧称或类别搜索，按教学区、生活东区、'
            '生活西区筛选。选择列表地点可在官方示意图中定位并查看来源；规划建筑默认隐藏。'
            '课设算路演示模式保留示例地图、地点详情和算法算路。'),
    }
    for document in knowledge:
        if document['id'] in updates:
            document['content'] = updates[document['id']]
            document['verified_on'] = '2026-11-23'
        if document['id'] == 'campus-map':
            document['source_url'] = ARTICLE
    for place in places:
        old_names = '、'.join(place['aliases'])
        content = (f"学校2026年官方校园示意图将{place['name']}列于{place['region']}，"
                   f"本项目归类为{place['category']}。")
        if old_names:
            content += f"2026年命名公告中的原名称或命名范围为：{old_names}。"
        if place['planned']:
            content += '来源标注为规划中，不能据此认为已建成或开放。'
        content += '这里只核对了公开文件，不确认实时开放情况或实际通行路线。'
        knowledge.append(dict(id='public-place-'+place['id'],title=place['name']+'官方资料',
            content=content,keywords=' '.join([place['name'],*place['aliases'],place['region'],place['category']]),
            source_url=ARTICLE if old_names else PDF,source_type='official',verified_on='2026-11-23'))
    # 对外服务说明保持与统一产品一致，历史过程仅留在开发文档中。
    product = {
        'campus-map': ('校园地图与资料来源','官网提供2026年大学城校区地图附件。校园示意图用于浏览地点，标记为近似图上位置，不是GPS坐标或入口。步行路线可通过页面衔接百度地图查询。','地图 示意图 平面图 官方 来源 查看 大学城'),
        'project-demo': ('导览服务与信息说明','平台提供校园地点目录、地图探索、收藏、步行地图与知识问答。校园示意图用于浏览，不是GPS导航；未确认的开放时间与道路距离不会作为事实给出。地点来源与资料日期可在详情中查看。','导览 数据 来源 地点 坐标 经纬度 示意图 导航 使用说明'),
        'project-search': ('地点探索与收藏','可以按地点名称、旧称或类别搜索，按教学区、生活东区、生活西区筛选。选择地点可定位地图、收藏或设为起终点。收藏保存在当前浏览器；规划建筑默认隐藏。','搜索 收藏 筛选 地图 详情 旧称 名称 区域'),
        'project-route': ('步行路线与智能问路','选择校园目录中的起点和终点后，可以打开百度地图查询步行路线，也可以用智能问路识别地点。实际步行距离与通行信息由地图服务提供，请核对其匹配的具体地点。规划建筑不提供步行路线查询。','路线 步行 问路 起点 终点 距离 导航 百度'),
        'project-admin': ('校园管理中心','管理员登录后可维护与访客共用的校园目录，包括地点名称、区域、类别、旧称、介绍、图上位置与资料来源。维护后的信息由目录与助手实时读取，管理员权限与普通浏览权限分离。','管理中心 管理员 登录 修改 删除 新增 保存 权限 账号'),
    }
    for document in knowledge:
        if document['id'] in product:
            document['title'],document['content'],document['keywords'] = product[document['id']]
            document['verified_on']='2026-11-24'
    knowledge_file.write_text(json.dumps(knowledge,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'places':len(places),'planned':sum(p['planned'] for p in places),'roads':0}))


if __name__ == '__main__':
    main()
