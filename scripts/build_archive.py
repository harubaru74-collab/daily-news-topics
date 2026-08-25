#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily-news-topics（時事おしゃべりネタ帳）アーカイブページ自動ビルドスクリプト

daily-topics/*.md を読み込み、archive/shell-topics.html を土台にして、
静的なアーカイブHTML（docs/index.html）を組み立てる。

このスクリプトはClaudeを一切使わない。GitHub Actionsから深夜2:00の
git push時に自動実行され、GitHub Pagesがそのままdocs/を公開する
（詳しくは archive/AUTOBUILD.md 参照）。

姉妹プロジェクト roumu-news の scripts/build_archive.py と同じ設計方針
（AI不使用・パース失敗しても処理を止めない）。変換ルールは
archive/BUILD-TOPICS.md に準拠。
"""
import glob
import html
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(REPO_ROOT, "daily-topics")
SHELL_PATH = os.path.join(REPO_ROOT, "archive", "shell-topics.html")
OUT_PATH = os.path.join(REPO_ROOT, "docs", "index.html")

SECTION_LABELS = ["何が起きた？", "世間の反応", "論点", "もし聞かれたら、こう答えられる"]


def esc(s):
    return html.escape(s or "", quote=False)


def inline_md(s):
    """HTMLエスケープした上で、**bold** だけ <strong> に変換する。"""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s.strip()


# ---------------------------------------------------------------------------
# 1トピックのパース
# ---------------------------------------------------------------------------

def parse_glossary(rest):
    m = re.match(r"^\s*>\s*📖\s*\*\*用語解説：(.+?)\*\*\s*\n((?:>.*(?:\n|$))*)", rest)
    if not m:
        return "", rest
    title = m.group(1).strip()
    body_lines = []
    for line in m.group(2).split("\n"):
        line = line.strip()
        if line.startswith(">"):
            line = line[1:].strip()
        if line:
            body_lines.append(line)
    body = " ".join(body_lines)
    html_out = (
        f'<div class="glossary"><strong>用語解説：{inline_md(title)}</strong>'
        f'<br />{inline_md(body)}</div>'
    )
    return html_out, rest[m.end():].lstrip("\n")


def parse_sections(rest):
    """**何が起きた？** 〜 **もし聞かれたら、こう答えられる** の4ブロックを順にパースする。"""
    out = []
    for i, label in enumerate(SECTION_LABELS):
        next_labels = SECTION_LABELS[i + 1:] + ["🔗 情報源", "🔗 参考"]
        pattern = (
            r"^\*\*" + re.escape(label) + r"\*\*\s*\n(.*?)"
            r"(?=\n\*\*(?:" + "|".join(re.escape(l) for l in next_labels) + r")\*\*|\Z)"
        )
        m = re.search(pattern, rest, re.DOTALL | re.MULTILINE)
        if not m:
            continue
        body = m.group(1).strip()
        if label == "もし聞かれたら、こう答えられる":
            out.append(
                f"<h4>{label}</h4>"
                f'<div class="answer-box"><span class="answer-label">💬 一言コメント案</span>'
                f"<p>{inline_md(body)}</p></div>"
            )
        else:
            out.append(f"<h4>{label}</h4><p>{inline_md(body)}</p>")
    return "".join(out)


def parse_source(rest):
    # 1記事に複数リンクがある場合も拾う（同じ行に複数 [text](url) が並ぶケース）
    m = re.search(r"\*\*🔗\s*(情報源|参考)\*\*\s*[：:]\s*(.+)", rest)
    if not m:
        return ""
    label, link_part = m.group(1), m.group(2)
    links = re.findall(r"\[(.+?)\]\((\S+?)\)", link_part)
    if not links:
        return ""
    anchors = "　".join(
        f'<a href="{esc(url)}" target="_blank" rel="noopener">{inline_md(text)}</a>'
        for text, url in links
    )
    return f'<p class="source-line">🔗 {label}：{anchors}</p>'


def build_article_html(block, genre):
    lines = block.strip("\n").split("\n")
    heading = lines[0].strip()
    rest = "\n".join(lines[1:]).strip("\n")

    glossary_html, rest = parse_glossary(rest)
    sections_html = parse_sections(rest)
    source_html = parse_source(rest)

    parts = [
        f'<span class="genre-tag">{inline_md(genre)}</span>',
        f"<h3>{inline_md(heading)}</h3>",
        glossary_html,
        sections_html,
        source_html,
    ]
    return '<article class="article">' + "".join(p for p in parts if p) + "</article>", heading


def extract_topic_blocks(text):
    """`## N. ジャンル｜見出し` ごとにブロックへ分割する。冒頭の説明文・末尾の注記は除く。"""
    # 冒頭のH1タイトル行＋説明文＋最初の --- を除去
    body = re.sub(r"^#[^\n]*\n+.*?\n+---\n+", "", text, count=1, flags=re.DOTALL)
    # 末尾の --- と斜体注記を除去
    body = re.sub(r"\n+---\s*\n+\*[^\n]*\*\s*$", "", body, flags=re.DOTALL).strip()
    parts = re.split(r"\n##\s+", "\n" + body)
    parts = [p for p in parts if p.strip()]
    blocks = []
    for p in parts:
        p = re.sub(r"\n+---\s*$", "", p.strip())
        blocks.append(p)
    return blocks


def parse_day_file(path):
    text = open(path, encoding="utf-8").read()
    blocks = extract_topic_blocks(text)
    topics = []
    for b in blocks:
        first_line = b.split("\n", 1)[0].strip()
        # "N. ジャンル｜見出し" を分解
        m = re.match(r"^\d+\.\s*(.+?)｜(.+)$", first_line)
        genre = m.group(1).strip() if m else ""
        heading = m.group(2).strip() if m else first_line
        # build_article_html には「見出し行＋残り」を渡すので、先頭行を見出しのみに差し替える
        rebuilt_block = heading + "\n" + b.split("\n", 1)[1] if "\n" in b else heading
        try:
            article_html, _ = build_article_html(rebuilt_block, genre)
        except Exception as e:  # noqa: BLE001 - ビルドを止めないためのフォールバック
            print(f"  [WARN] {os.path.basename(path)}: 記事のパースに失敗しました ({e})", file=sys.stderr)
            article_html = (
                f'<article class="article"><span class="genre-tag">{inline_md(genre)}</span>'
                f"<h3>{inline_md(heading)}</h3>"
                f'<p class="source-line">（自動変換に失敗した記事です。手動確認が必要）</p></article>'
            )
        topics.append((genre, heading, article_html))
    return topics


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def month_label(y, mo):
    return f"{y}年{int(mo)}月"


def main():
    day_files = sorted(
        f for f in glob.glob(os.path.join(TOPICS_DIR, "*.md"))
        if re.match(r"\d{4}-\d{2}-\d{2}\.md$", os.path.basename(f))
    )
    if not day_files:
        print("daily-topics/*.md が見つかりません。中断します。", file=sys.stderr)
        sys.exit(1)

    # 新しい日付が先に来るよう降順に並べる
    day_files_desc = list(reversed(day_files))

    oldest_date = os.path.basename(day_files[0])[:10]
    y0, mo0, d0 = oldest_date.split("-")
    issue_range_label = f"創刊 {y0}年{int(mo0)}月{int(d0)}日"
    issue_count = len(day_files_desc)

    out_blocks = []
    prev_month_key = None
    for i, path in enumerate(day_files_desc):
        date_str = os.path.basename(path)[:10]
        y, mo, d = date_str.split("-")
        month_key = f"{y}-{mo}"

        if month_key != prev_month_key:
            out_blocks.append(f'<div class="month-divider">{month_label(y, mo)}</div>')
            prev_month_key = month_key

        is_open = " open" if i == 0 else ""

        topics = parse_day_file(path)
        n = len(topics)
        headline = topics[0][1] if topics else "（記事なし）"
        if len(headline) > 20:
            headline = headline[:20] + "…"
        sub = "／".join(h for _, h, _ in topics) + f"　全{n}件"
        search_kw = " ".join(f"{g} {h}" for g, h, _ in topics)
        search_kw = re.sub(r"[「」『』（）()【】、。！？!?\"'”“]", " ", search_kw)
        body_html = "\n".join(a for _, _, a in topics)
        badge = f"{int(mo)}/{int(d)}"

        out_blocks.append(
            f'<details class="issue" id="topics-{date_str}"{is_open} data-search="{esc(search_kw)}">\n'
            f'      <summary>\n'
            f'        <span class="issue-badge">{esc(badge)}</span>\n'
            f'        <span>\n'
            f'          <span class="issue-headline">{inline_md(headline)}</span>\n'
            f'          <span class="issue-sub">{inline_md(sub)}</span>\n'
            f'        </span>\n'
            f'        <span class="issue-toggle" aria-hidden="true">▾</span>\n'
            f'      </summary>\n'
            f'      <div class="issue-body">\n'
            f'{body_html}\n'
            f'      </div>\n'
            f'    </details>'
        )

    issues_html = "\n\n    ".join(out_blocks)

    shell = open(SHELL_PATH, encoding="utf-8").read()
    # shell.html先頭のドキュメント用HTMLコメント（人間向けの説明。中に
    # "ISSUES_GO_HERE" という文字列が例示として出てくるため、置換前に必ず除去する。
    # これを忘れると本文中の説明文にもマッチして記事が二重に差し込まれる
    # （実際に一度この不具合を踏んだので、必ずここで先に除去する）。
    shell = re.sub(r"^\s*<!--.*?-->\s*\n", "", shell, count=1, flags=re.DOTALL)
    shell = shell.replace("<!-- ISSUES_GO_HERE -->", issues_html)
    shell = shell.replace("{{ISSUE_RANGE}}", issue_range_label)
    shell = shell.replace("全{{ISSUE_COUNT}}日分", f"全{issue_count}日分")
    shell = shell.replace("{{ISSUE_COUNT}}", str(issue_count))

    # shell-topics.html はArtifact用の「body断片」として作られてきた経緯があるので、
    # <!DOCTYPE html>/<head>/<meta viewport> 等がない。GitHub PagesではArtifactを
    # 経由しないため、ここで正式なHTML文書として組み立て直す。
    # （viewportがないとスマホでデスクトップ表示扱いされ、極端に縮小されてしまう）
    shell = shell.replace(
        "<title>",
        (
            '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "<title>"
        ),
        1,
    )
    shell = shell.replace("</style>", "</style>\n</head>\n<body>", 1)
    shell = shell.rstrip() + "\n</body>\n</html>\n"

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(shell)

    print(f"OK: {issue_count}日分を {OUT_PATH} に出力しました（創刊={issue_range_label}）")


if __name__ == "__main__":
    main()
