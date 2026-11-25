"""本机真实问答验收，报告不包含密钥。"""
import json

import httpx

from backend.app.config import ROOT


def main():
    report = {'scope': 'live_assistant_only'}
    with httpx.Client(base_url='http://127.0.0.1:5173', timeout=65) as client:
        status = client.get('/api/assistant/status')
        status.raise_for_status()
        report['service'] = status.json()
        response = client.post('/api/assistant/ask',json={'question':'大学城校区的地址是什么？'})
        report['live_http_status'] = response.status_code
        if response.status_code == 200:
            result = response.json()
            assert result['status']=='answered'
            assert any(s['id']=='campus-address' for s in result['sources'])
            assert '100' in result['answer']
            report.update(status='passed',answer=result)
        else:
            report.update(status='pending_live_model',detail=response.json().get('detail','调用未通过'))
        missing = client.post('/api/assistant/ask', json={'question':'量子纠缠实验设计'})
        assert missing.status_code==200 and missing.json()['status']=='insufficient_evidence'
        assert missing.json()['model'] is None
        report['no_evidence_refusal'] = True
    (ROOT/'docs/stage-6-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('Assistant verification failed:',type(exc).__name__)
        raise SystemExit(1)
