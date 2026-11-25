"""免费本地字词哈希向量 + Chroma 检索；不是预训练语义嵌入。"""
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from backend.app.config import ROOT

KNOWLEDGE_FILE = ROOT / 'data/knowledge/campus.json'
DIMENSION = 1024


def tokens(text: str) -> set[str]:
    text = text.lower()
    result = set(re.findall(r'[a-z0-9]+', text))
    for part in re.findall(r'[\u4e00-\u9fff]+', text):
        # 二字和三字窗口保留中文词形，同时避免单字造成过多误匹配。
        for width in (2, 3):
            result.update(part[i:i+width] for i in range(len(part)-width+1))
    return result


def vector(text: str) -> list[float]:
    values = [0.0] * DIMENSION
    for token in tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], 'little') % DIMENSION
        values[index] += 1 if digest[4] % 2 else -1
    length = math.sqrt(sum(v*v for v in values))
    return [v/length for v in values] if length else values


class KnowledgeIndex:
    def __init__(self, directory: Path):
        import chromadb
        from chromadb.config import Settings
        self.documents = json.loads(KNOWLEDGE_FILE.read_text(encoding='utf-8'))
        if len({d['id'] for d in self.documents}) != len(self.documents):
            raise ValueError('知识条目编号重复')
        fingerprint = hashlib.sha256(KNOWLEDGE_FILE.read_bytes()).hexdigest()[:16]
        self.client = chromadb.PersistentClient(path=str(directory), settings=Settings(anonymized_telemetry=False))
        # 内容指纹隔离旧版本，避免修改或删除文档后检索出陈旧记录。
        self.collection = self.client.get_or_create_collection(
            'campus_' + fingerprint, embedding_function=None, metadata={'hnsw:space':'cosine'})
        self.by_id = {d['id']: d for d in self.documents}
        if self.collection.count() != len(self.documents):
            texts = [d['title']+' '+d['keywords']+' '+d['content'] for d in self.documents]
            self.collection.upsert(ids=list(self.by_id), documents=texts, embeddings=[vector(t) for t in texts])

    def retrieve(self, question: str) -> list[dict]:
        terms = tokens(question)
        if not terms:
            return []
        result = self.collection.query(query_embeddings=[vector(question)],
            n_results=min(5, len(self.documents)), include=['distances'])
        matches = []
        # 官方地点专名很短，纯字词向量可能因长正文稀释而漏召回。
        # 明确包含完整地点名的查询优先保留该资料，再由模型判断能否回答问题。
        named = {d['id']: d for d in self.documents
                 if d['id'].startswith('public-place-')
                 and d['title'].removesuffix('官方资料') in question}
        if '示意图' in question and any(t in question.lower() for t in ('导航','gps','定位','真实')):
            if 'project-demo' in self.by_id:
                named['project-demo'] = self.by_id['project-demo']
        matches.extend({**d, 'score': 1.0} for d in named.values())
        for document_id, distance in zip(result['ids'][0], result['distances'][0]):
            if document_id in named:
                continue
            document = self.by_id[document_id]
            overlap = terms & tokens(document['title']+' '+document['keywords']+' '+document['content'])
            score = 1 - distance
            if overlap and score >= 0.12:
                matches.append({**document, 'score': round(score, 4)})
        return matches[:3]


@lru_cache(maxsize=1)
def get_index():
    return KnowledgeIndex(ROOT / '.runtime/chroma')
