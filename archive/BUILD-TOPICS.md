# アーカイブページ（時事おしゃべりネタ）の変換ルール

**2026-08-25〜、この手順はもう手動では実行しない。** `scripts/build_archive.py` が
このドキュメントに書かれた変換ルールをそのままPythonで実装していて、GitHub Actions経由で
自動的に実行される。詳しくは `archive/AUTOBUILD.md` を参照。

このドキュメント自体は、**Markdown → HTMLの変換ルールの正式な仕様書**として今も有効。
`scripts/build_archive.py` を直すときはここを参照する。

（このファイルはもともと、Claude Artifactとして手動で毎晩再公開していた旧方式（〜2026-08-25）の
手順書だった。`archive/BUILD.md`（労務ニュース）の姉妹版として作られた経緯がある。）

## 手順（旧・Claude手動運用時代の記録）

1. `archive/shell-topics.html` を読み込む（デザイン部分の土台）。
2. `daily-topics/*.md` を**ファイル名（日付）の降順**（新しい日付が先）で全て読み込む。
3. 各ファイルを以下のルールで `<details class="issue">...</details>` ブロックに変換する。
4. 月が変わる境目に `<div class="month-divider">YYYY年M月</div>` を挿入する。
5. 最新（一番上）の号だけ `open` 属性をつける。
6. `shell-topics.html` の `<!-- ISSUES_GO_HERE -->` の位置に、変換した全issueブロックを差し込む。
7. `{{ISSUE_COUNT}}` を号数（ファイル数）に、`{{ISSUE_RANGE}}` を「創刊 YYYY年M月D日」（一番古いファイルの日付）に置換する。
8. 完成したHTMLを一時ファイルに保存し、Artifactツールで上記の固定URLを指定して再公開する（favicon: 💬、title: "時事おしゃべりネタ帳 — アーカイブ"）。

## Markdown → HTMLの変換ルール

`daily-topics/YYYY-MM-DD.md` は、`ROUTINE-TOPICS.md` で定めた以下の構成で書かれている（冒頭の説明文、末尾の注記は含まない）：

```
## N. ジャンル名｜見出し

> 📖 **用語解説：〇〇って何？**
> 本文...（専門用語がある記事のみ。無い記事は丸ごと省略）

**何が起きた？**
本文...

**世間の反応**
本文...

**論点**
本文...

**もし聞かれたら、こう答えられる**
本文...

**🔗 情報源**：[サイト名「記事タイトル」](URL)
```

これを1ファイル＝1つの `<details class="issue">` として扱い、ファイル内の `## N. ...` ごとに1つの `<article class="article">` に変換する：

| Markdown | HTML |
|---|---|
| `## N. ジャンル名｜見出しテキスト` | `<article class="article"><span class="genre-tag">ジャンル名</span><h3>見出しテキスト</h3>` |
| `> 📖 **用語解説：...**\n> ...`（ある場合のみ） | `<div class="glossary"><strong>用語解説：...</strong><br />...</div>` |
| `**何が起きた？**`\n本文 | `<h4>何が起きた？</h4><p>本文</p>`（`**太字**` は `<strong>` に変換） |
| `**世間の反応**`\n本文 | `<h4>世間の反応</h4><p>本文</p>` |
| `**論点**`\n本文 | `<h4>論点</h4><p>本文</p>` |
| `**もし聞かれたら、こう答えられる**`\n本文 | `<h4>もし聞かれたら、こう答えられる</h4><div class="answer-box"><span class="answer-label">💬 一言コメント案</span><p>本文</p></div>` |
| `**🔗 情報源**：[サイト名「タイトル」](URL)` | `<p class="source-line">🔗 情報源：<a href="URL" target="_blank" rel="noopener">サイト名「タイトル」</a></p>`（複数リンクがある記事は同じ `<p>` 内に並べる） |

`<details>` の `summary` 部分：
```html
<summary>
  <span class="issue-badge">M/D</span>
  <span>
    <span class="issue-headline">（その日を象徴する短いキャッチコピー、20字程度）</span>
    <span class="issue-sub">（各トピックの見出しを「／」区切りで列挙）　全N件</span>
  </span>
  <span class="issue-toggle" aria-hidden="true">▾</span>
</summary>
```
`issue-headline` はその日で一番話題性の高いトピックを軸に、新しく短く要約して作ってよい（元の見出しの丸写しでなくてOK）。

`data-search` 属性には、各トピックのジャンル名・キーワードをスペース区切りで詰め込む（検索用）。

`id` 属性は `topics-YYYY-MM-DD` の形式にする（労務ニュース側の `issue-YYYY-MM-DD` と重複しないよう、プレフィックスを変えている）。

冒頭の「## 目的」セクションと末尾の「*本まとめは...*」の注記は、アーカイブページには含めない（フッターに同趣旨の文言が既に入っているため）。

## 注意事項

- HTML特殊文字（`&` `<` `>`）はエスケープすること。
- 既存の号の内容は変更しない（過去の daily-topics/*.md の中身をそのまま変換するだけ）。
- 再公開が失敗した場合も、GitHubへのpush自体は既に完了していれば、アーカイブ更新の失敗は致命的ではない。失敗した旨だけ通知に含めればよい。
- 月次まとめは現時点では未対応（労務ニュース側の `news/monthly/` に相当する仕組みはまだない）。将来必要になったら `archive/BUILD.md` の該当セクションを参考に追加する。
