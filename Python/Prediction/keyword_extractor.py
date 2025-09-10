# c:\Users\3CLASS_008\Documents\GitHub\3team\Python\Prediction\keyword_extractor.py
# -*- coding: utf-8 -*-

import re
import math
from collections import Counter, defaultdict
from konlpy.tag import Okt
import networkx as nx

# 재무/투자/거시 키워드 정규식 (도메인 보너스에 사용)
FIN_TERMS   = r"(매출|영업이익|순이익|EPS|ROE|마진|영업이익률|순이익률|성장률|컨센서스|가이던스|YoY|QoQ|분기|실적)"
INV_TERMS   = r"(투자의견|매수|중립|매도|목표주가|밸류에이션|PER|PBR|EV/EBITDA|리레이팅|디스카운트)"
MACRO_TERMS = r"(금리|환율|유가|인플레이션|수요|공급|재고|가동률|원자재|경기|정책|규제|수출규제|반덤핑|관세)"

# 불용어(자유롭게 추가/수정)
STOPWORDS = set("""
그리고 그러나 또한 또한은 및 대한 대해서 관련 위한 해당 이것 그것 보고서 본문 회사 당사 기존 이번 다음 각각 전반 특히 다만
""".split())
DOMAIN_STOP = set("""
분기 실적 추정 개선 영향 기반 수준 결과 경우 향후 최근 전체 일부 전년 전분기 당분기 전망
""".split())

class KeywordExtractor:
    def __init__(self, company_lexicon=None):
        """
        company_lexicon: 기업명/티커 사전(set[str]) (선택)
        """
        self.okt = Okt()
        self.company_lexicon = set(company_lexicon or [])

    # ------------ 내부 유틸 ------------
    def _normalize(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _sent_tokenize(self, text: str):
        # 간단한 문장 분할
        sents = re.split(r"(?<=[\.!?])\s+|(?<=\n)\s*", text)
        return [s.strip() for s in sents if s and s.strip()]

    def _tokens(self, sentence: str):
        # 명사/알파벳(약어) 중심
        toks = []
        for w, p in self.okt.pos(sentence, stem=True, norm=True):
            if p == "Noun" and len(w) > 1 and w not in STOPWORDS:
                toks.append(w)
            elif p in ("Alpha", "Foreign"):  # PER, PBR, QoQ 등
                toks.append(w)
        return toks

    def _make_ngrams(self, tokens, n=3):
        # 1글자 한글 토큰이 포함된 n-gram은 제외하여 '기 발표' 같은 파편을 방지
        def _has_single_hangul(toks):
            for t in toks:
                if len(t) == 1 and re.search(r"[가-힣]", t):
                    return True
            return False

        grams = []
        L = len(tokens)
        for k in range(1, n+1):
            for i in range(L-k+1):
                span = tokens[i:i+k]
                if _has_single_hangul(span):
                    continue
                grams.append(" ".join(span))
        return grams

    def _textrank_scores(self, sentences_tokens, window=4):
        G = nx.Graph()
        for toks in sentences_tokens:
            for i, u in enumerate(toks):
                for j in range(i+1, min(i+window, len(toks))):
                    v = toks[j]
                    if u == v:
                        continue
                    if not G.has_edge(u, v):
                        G.add_edge(u, v, weight=1)
                    else:
                        G[u][v]["weight"] += 1
        if len(G) == 0:
            return {}
        return nx.pagerank(G, weight="weight")

    def _domain_bonus_and_cat(self, phrase: str):
        bonus = 0.0
        cat = []
        if re.search(FIN_TERMS, phrase, flags=re.IGNORECASE):
            bonus += 0.25; cat.append("재무·실적")
        if re.search(INV_TERMS, phrase, flags=re.IGNORECASE):
            bonus += 0.25; cat.append("투자판단")
        if re.search(MACRO_TERMS, phrase, flags=re.IGNORECASE):
            bonus += 0.20; cat.append("시장·산업")
        for c in self.company_lexicon:
            if c in phrase:
                bonus += 0.25; cat.append("기업/제품")
                break
        if not cat:
            cat.append("기타")
        return bonus, list(set(cat))

    # ------------ 공개 메서드 ------------
    def extract_keywords(self, text_or_news, num_keywords=10, return_detail=False):
        """
        text_or_news:
          - str: 원문 텍스트
          - list[dict]: [{'title': str, 'content': str}, ...]
        num_keywords: 상위 몇 개 키워드
        return_detail: True면 [{'keyword','score','category','evidence'}] 반환
                       False면 ['키워드', ...]만 반환
        """
        # 1) 입력 정규화 + 문장/토큰화 준비
        docs = []
        if isinstance(text_or_news, str):
            docs.append({"text": self._normalize(text_or_news), "title": False})
        elif isinstance(text_or_news, list):
            for item in text_or_news:
                title = self._normalize(str(item.get("title", "")))
                body  = self._normalize(str(item.get("content", "")))
                if title:
                    docs.append({"text": title, "title": True})
                if body:
                    docs.append({"text": body, "title": False})
        else:
            return [] if not return_detail else []

        # 2) 문장/토큰, 위치·제목 가중치 계산 준비
        all_sents = []
        sent_meta = []  # (is_title, sent_idx_in_doc)
        for d in docs:
            sents = self._sent_tokenize(d["text"]) or [d["text"]]
            for idx, s in enumerate(sents):
                all_sents.append(s)
                sent_meta.append((d["title"], idx))  # 제목 여부, 해당 문서 내 문장 순서

        if not all_sents:
            return [] if not return_detail else []

        sent_tokens = [self._tokens(s) for s in all_sents]
        total_sents = len(sent_tokens)

        # 3) TextRank (단어 랭크)
        word_rank = self._textrank_scores(sent_tokens, window=4)

        # 4) n-gram 후보, TF 집계, 메타(위치/제목/근거)
        cand_counter = Counter()
        meta = defaultdict(lambda: {"positions": [], "is_title_hit": False, "evidence": ""})

        for global_idx, toks in enumerate(sent_tokens):
            grams = self._make_ngrams(toks, n=3)
            is_title, sent_idx_in_doc = sent_meta[global_idx]

            for g in grams:
                cand_counter[g] += 1
                meta[g]["positions"].append(global_idx)
                meta[g]["is_title_hit"] = meta[g]["is_title_hit"] or is_title
                if not meta[g]["evidence"]:
                    meta[g]["evidence"] = all_sents[global_idx][:220]

        # 5) 스코어 계산 (TF + 위치 + 제목 + TextRank + 도메인 보너스)
        scores = {}
        for phrase, tf in cand_counter.items():
            # TF (로그 스케일)
            tf_score = 1 + math.log(tf, 2)

            # 위치 가중치: 앞 문장일수록 가중↑
            pos_weights = []
            for p in meta[phrase]["positions"]:
                ratio = 1.0 - (p / max(1, total_sents - 1))
                pos_weights.append(0.8 + 0.4 * ratio)  # 0.8 ~ 1.2
            pos_score = sum(pos_weights) / max(1, len(pos_weights))

            # 제목 가중치
            title_boost = 1.15 if meta[phrase]["is_title_hit"] else 1.0

            # TextRank: 구성 단어 평균
            ws = phrase.split()
            tr_vals = [word_rank.get(w, 0.0) for w in ws]
            tr_score = sum(tr_vals) / len(ws) if ws else 0.0

            # 도메인 보너스 & 카테고리
            dom_bonus, cats = self._domain_bonus_and_cat(phrase)

            # 길이 패널티(너무 긴 n-gram 억제)
            len_penalty = 1.0 - 0.05 * max(0, len(ws) - 2)

            final = (
                0.50 * tf_score +
                0.15 * pos_score +
                0.15 * tr_score
            ) * title_boost
            final = final + dom_bonus
            final = final * len_penalty

            # 단일 토큰이 도메인 잦은 단어만으로 구성된 경우 약한 패널티 적용
            if len(ws) == 1 and ws[0] in DOMAIN_STOP:
                final *= 0.65

            scores[phrase] = (final, cats)

        # 6) 랭킹 및 부분중복 정리(상위 표현 우선)
        ranked = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
        picked = []
        used = []

        for ph, (sc, cats) in ranked:
            if any(ph in u for u in used):  # 더 강한 상위 표현에 포함되면 스킵
                continue
            picked.append({
                "keyword": ph,
                "score": round(sc, 4),
                "frequency": cand_counter[ph]
                # "category": cats,
                # "evidence": meta[ph]["evidence"]
            })
            used.append(ph)
            if len(picked) >= num_keywords:
                break

        if return_detail:
            return picked
        return [p["keyword"] for p in picked]
