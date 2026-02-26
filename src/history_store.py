#!/usr/bin/env python3
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def _safe_read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class HistoryStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_file = self.root / "index.json"
        self.index = _safe_read_json(self.index_file) or {"dates": {}}

    def _date_file(self, date_str: str) -> Path:
        return self.root / f"{date_str}.jsonl"

    def append_messages(self, messages: List[Dict]):
        if not messages:
            return

        grouped: Dict[str, List[Dict]] = {}
        for msg in messages:
            t = msg.get("time", "")
            date_str = self._extract_date(t)
            grouped.setdefault(date_str, []).append(msg)

        for date_str, items in grouped.items():
            file = self._date_file(date_str)
            with file.open("a", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            self._rebuild_index_for_date(date_str)

        self._save_index()

    def load_date_history(self, date_str: str) -> List[Dict]:
        file = self._date_file(date_str)
        if not file.exists():
            return []
        rows = []
        for line in file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
        return rows

    def load_today_history(self) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.load_date_history(today)

    def list_dates(self) -> List[Dict]:
        items = []
        for date_str, meta in self.index.get("dates", {}).items():
            row = {"date": date_str}
            if isinstance(meta, dict):
                row.update(meta)
            items.append(row)
        items.sort(key=lambda x: x.get("date", ""), reverse=True)
        return items

    def search_dates(self, query: str) -> List[Dict]:
        q = (query or "").strip().lower()
        if not q:
            return self.list_dates()

        results = []
        for row in self.list_dates():
            topics = " ".join(row.get("topics", []))
            summary = row.get("summary", "")
            hay = f"{row.get('date', '')} {topics} {summary}".lower()
            if q in hay:
                results.append(row)
        return results

    def recall_notes_for_query(self, query: str, limit: int = 3) -> str:
        query_tokens = self._extract_tokens(query)
        if not query_tokens:
            ranked = self.list_dates()[:limit]
        else:
            ranked = sorted(
                self.list_dates(),
                key=lambda row: self._score_row(row, query_tokens),
                reverse=True,
            )[:limit]

        lines = []
        for row in ranked:
            topics = "、".join(row.get("topics", [])[:6]) or "无"
            summary = row.get("summary", "无摘要")
            lines.append(f"- {row.get('date')}: 话题[{topics}]；摘要：{summary}")
        return "\n".join(lines)

    def _score_row(self, row: Dict, query_tokens: List[str]) -> int:
        score = 0
        topics = [x.lower() for x in row.get("topics", []) if isinstance(x, str)]
        summary = (row.get("summary", "") or "").lower()
        for token in query_tokens:
            if token.lower() in topics:
                score += 5
            if token.lower() in summary:
                score += 2
        # Prefer recent rows when score ties.
        return score

    def _rebuild_index_for_date(self, date_str: str):
        rows = self.load_date_history(date_str)
        user_texts = [x.get("text", "") for x in rows if x.get("role") == "user"]
        topics = self._extract_top_topics("\n".join(user_texts), topn=8)
        highlights = [self._shorten(x) for x in user_texts[:5]]
        summary = self._build_summary(topics, highlights)

        self.index.setdefault("dates", {})[date_str] = {
            "topics": topics,
            "summary": summary,
            "highlights": highlights,
            "turns": len(user_texts),
            "messages": len(rows),
            "updated_at": datetime.now().isoformat(),
        }

    def _build_summary(self, topics: List[str], highlights: List[str]) -> str:
        topic_text = "、".join(topics[:5]) if topics else "未提取到明显主题"
        if highlights:
            return f"主要围绕 {topic_text}；核心问题包括：{'; '.join(highlights[:3])}"
        return f"主要围绕 {topic_text}"

    def _extract_top_topics(self, text: str, topn: int = 8) -> List[str]:
        tokens = self._extract_tokens(text)
        if not tokens:
            return []
        counts = Counter(tokens)
        return [k for k, _ in counts.most_common(topn)]

    def _extract_tokens(self, text: str) -> List[str]:
        if not text:
            return []
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}", text)
        stop = {
            "我们", "你们", "这个", "那个", "然后", "可以", "需要", "如何", "现在", "今天",
            "一下", "一个", "还有", "已经", "因为", "所以", "是否", "进行", "方案", "问题",
            "with", "that", "this", "from", "have", "should", "what", "when", "where",
        }
        out = []
        for w in words:
            ww = w.strip().lower()
            if len(ww) < 2 or ww in stop:
                continue
            out.append(w)
        return out

    def _extract_date(self, iso_time: str) -> str:
        if isinstance(iso_time, str) and len(iso_time) >= 10:
            return iso_time[:10]
        return datetime.now().strftime("%Y-%m-%d")

    def _shorten(self, text: str, n: int = 32) -> str:
        t = (text or "").replace("\n", " ").strip()
        if len(t) <= n:
            return t
        return t[:n] + "..."

    def _save_index(self):
        self.index_file.write_text(
            json.dumps(self.index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

