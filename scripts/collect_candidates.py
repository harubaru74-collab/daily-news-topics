#!/usr/bin/env python3
"""
候補トピックの自動収集スクリプト（AI不使用・純粋なPython/RSS収集）。
roumu-news側の scripts/collect_candidates.py の姉妹版（同じ設計思想）。

目的：
  深夜2:00のClaudeルーティンが毎回6ジャンル分をゼロからWeb検索している負荷を
  減らすため、Google News RSS（無料・APIキー不要）で候補トピックのタイトル・
  リンク・出典・掲載日を先に集めておき、`staging/candidates/YYYY-MM-DD.md` に
  書き出す。

重要な注意（Claude向け）：
  このファイルはAIを一切使わず機械的に集めた「リード（手がかり）」に過ぎない。
  タイトル・掲載日はRSS由来の情報をそのまま転記しているだけで、正確性・実在性は
  一切検証していない。ROUTINE-TOPICS.mdの非捏造原則・情報源の実在確認は従来通り
  Claude側で必ず行うこと（このスクリプトはその手前の下ごしらえでしかない）。

  なお「世間の反応」の検索（トピック確定後に個別に行う反応・賛否のリサーチ）は
  このスクリプトの対象外。これはトピックが決まってから初めて意味を持つ検索なので、
  従来通りClaude側でWeb検索すること。このスクリプトが省力化するのは、あくまで
  「今日〜直近数日で話題になっているトピック候補を探す」という最初の段階だけ。

実行方法：
  python3 scripts/collect_candidates.py
  （標準ライブラリのみで動作。pip install不要）
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
FRESHNESS_DAYS = 5  # ROUTINE-TOPICS.mdの「今日〜直近数日」に合わせた短めの窓
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 0.6
MAX_ITEMS_PER_QUERY = 6
USER_AGENT = (
    "Mozilla/5.0 (compatible; daily-news-topics-candidate-collector/1.0; "
    "+https://github.com/harubaru74-collab/daily-news-topics)"
)

# (表示名, [検索クエリ...])
# クエリの内容はROUTINE-TOPICS.mdの対象ジャンル・検索例をそのまま踏襲している。
CATEGORIES: list[tuple[str, list[str]]] = [
    (
        "経済・お金",
        ["値上げ ニュース 話題", "給料 ニュース 話題", "税金 ニュース", "景気 ニュース 話題"],
    ),
    (
        "社会・生活",
        [
            "社会 ニュース 話題",
            "制度変更 ニュース",
            "事件 トラブル ニュース 話題",
            "教育 ニュース 話題",
            "防災 ニュース",
        ],
    ),
    (
        "テック・AI",
        ["生成AI ニュース 話題", "新サービス IT ニュース", "IT 炎上 議論 ニュース"],
    ),
    (
        "仕事・キャリア",
        # 労務法制そのものはroumu-news側の担当なので、あえて含めない
        ["転職市場 ニュース 話題", "働き方 ニュース 話題", "企業 話題 ニュース"],
    ),
    (
        "エンタメ・SNS",
        ["エンタメ ニュース 話題", "SNS バズった 話題", "炎上 話題 ニュース"],
    ),
    (
        "国際・時事",
        ["国際ニュース 日本 関連", "海外 ニュース 話題 日本"],
    ),
]


@dataclass
class Candidate:
    title: str
    source: str
    link: str
    pub_date: datetime | None

    def dedup_key(self) -> str:
        # タイトル末尾の " - 出典名" を落とし、空白を除去して大まかに正規化する
        base = re.sub(r"\s*-\s*[^-]+$", "", self.title)
        return re.sub(r"\s+", "", base).lower()


def fetch_rss(query: str) -> list[Candidate]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "ja", "gl": "JP", "ceid": "JP:ja"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  [警告] 取得失敗: {query!r} ({e})", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"  [警告] XMLパース失敗: {query!r} ({e})", file=sys.stderr)
        return []

    out: list[Candidate] = []
    for item in root.findall("./channel/item")[:MAX_ITEMS_PER_QUERY]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        pub_date_raw = item.findtext("pubDate")
        pub_date = None
        if pub_date_raw:
            try:
                pub_date = parsedate_to_datetime(pub_date_raw)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pub_date = None
        out.append(Candidate(title=title, source=source, link=link, pub_date=pub_date))
    return out


def collect_category(queries: list[str], now_utc: datetime) -> list[Candidate]:
    cutoff = now_utc - timedelta(days=FRESHNESS_DAYS)
    seen: set[str] = set()
    results: list[Candidate] = []
    for q in queries:
        print(f"  検索中: {q}")
        for c in fetch_rss(q):
            key = c.dedup_key()
            if not key or key in seen:
                continue
            if c.pub_date is not None and c.pub_date < cutoff:
                continue
            seen.add(key)
            results.append(c)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return results


def format_candidate(c: Candidate) -> str:
    date_str = c.pub_date.astimezone(JST).strftime("%Y-%m-%d %H:%M") if c.pub_date else "掲載日不明"
    source = c.source or "出典不明"
    return f"- **{c.title}**（{source}, {date_str}）\n  {c.link}"


def main() -> None:
    now_utc = datetime.now(timezone.utc)
    today_jst = datetime.now(JST).strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# 候補トピックリスト（自動収集・AI不使用） {today_jst}")
    lines.append("")
    lines.append(
        "> ⚠️ これはGitHub ActionsがGoogle News RSSから機械的に集めた**未検証のリード一覧**です。"
        "タイトル・掲載日・出典はRSSの情報をそのまま転記しており、内容の正確性・実在性は一切保証されていません。"
        "採用する場合は必ず実際の記事を確認（WebFetch等）してから執筆すること。"
        "非捏造原則・情報源の実在確認はこれまで通りClaude側の責任で行うこと。"
        "「世間の反応」の検索は、このリストとは無関係にトピック確定後に個別に行うこと。"
        "ここに載っていない・不十分な場合は、従来通りWeb検索で補ってよい。"
    )
    lines.append("")

    total = 0
    for name, queries in CATEGORIES:
        print(f"[{name}]")
        items = collect_category(queries, now_utc)
        total += len(items)
        lines.append(f"## {name}")
        lines.append("")
        if not items:
            lines.append("（今回は候補が見つかりませんでした。Web検索でのフォールバックが必要です。）")
        else:
            for c in items:
                lines.append(format_candidate(c))
        lines.append("")

    out_dir = Path("staging/candidates")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today_jst}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n書き出し完了: {out_path}（候補{total}件）")


if __name__ == "__main__":
    main()
