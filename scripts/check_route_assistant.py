"""阶段 7 本机真实验收：模型抽取地点 + Dijkstra 真实算路 + 歧义拒答。报告不含密钥。"""
import json

import httpx

from backend.app.config import ROOT


def main():
    report = {'scope': 'live_route_assistant_only'}
    with httpx.Client(base_url='http://127.0.0.1:5173', timeout=70) as client:
        status = client.get('/api/assistant/route/status')
        status.raise_for_status()
        report['service'] = status.json()
        assert report['service']['tool'] == 'plan_route'

        # 真实模型工具调用：从北门到食堂，示例最短路应为 290 米，路径 NG->LIB->SC->DIN。
        response = client.post('/api/assistant/route', json={'question': '从北门到食堂怎么走'})
        report['live_http_status'] = response.status_code
        result = response.json()
        assert response.status_code == 200 and result['status'] == 'planned', result
        assert result['route']['start_id'] == 0 and result['route']['end_id'] == 6
        assert result['route']['distance_m'] == 290, result['route']['distance_m']
        assert [p['code'] for p in result['route']['path']] == ['NG', 'LIB', 'SC', 'DIN']
        assert result['model'] == 'XingChenAGI/Xing4.0-29B'
        assert result['extraction_method'] in ('model_tool', 'explicit_pattern')
        assert result['tool_used'] == (result['extraction_method'] == 'model_tool')
        report['planned_route'] = {
            'question': '从北门到食堂怎么走',
            'start_place': result['start_place'], 'end_place': result['end_place'],
            'distance_m': result['route']['distance_m'],
            'path': [p['code'] for p in result['route']['path']],
            'extraction_method': result['extraction_method'],
            'tool_used': result['tool_used'],
        }

        # 模型不得编造：歧义地点和不存在的地点都必须要求澄清，且不返回路线。
        for question in ('从教学楼到食堂', '从火星基地到食堂'):
            refused = client.post('/api/assistant/route', json={'question': question})
            assert refused.status_code == 200
            body = refused.json()
            assert body['status'] == 'need_clarification' and body['route'] is None, body
        report['ambiguous_and_unknown_refused'] = True
    (ROOT / 'docs/stage-7-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
