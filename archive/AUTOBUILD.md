# アーカイブページの自動ビルド（2026-08-25〜、Claude不使用）

roumu-news（労務ニュース）で先に導入した仕組みと同じもの。姉妹プロジェクト。

## 移行の経緯

このプロジェクト（daily-topics / 時事おしゃべりネタ帳）は、もともと `roumu-news` リポジトリの
`claude/daily-news-topics-routine-ak81mg` ブランチに間借りする形で運用していて、アーカイブページは
Claudeが毎晩手作業でHTMLを組み立ててClaude Artifactに再公開する方式だった。

2026-08-25、roumu-news側がGitHub Actions + GitHub Pagesによる完全自動更新に移行したのに合わせて、
このプロジェクトも同じ仕組みに移行し、あわせて**専用リポジトリ（このリポジトリ）に分離**した
（GitHub Pagesは1リポジトリにつき1サイトしか持てないため、roumu-newsと同居させると衝突するため）。

## 仕組み

```
daily-topics/*.md が git push される
        ↓
GitHub Actions（.github/workflows/build-archive.yml）が起動
        ↓
scripts/build_archive.py（Pythonスクリプト・AI不使用）が
  daily-topics/*.md + archive/shell-topics.html を読み込んで
  docs/index.html を組み立てる
        ↓
GitHub Pagesが docs/ を自動公開
```

**Claudeが関与するのは「daily-topics/*.md を書いてgit pushするところ」まで。** そこから先（アーカイブHTMLの組み立て・公開）は完全にGitHub側で完結し、トークンを一切消費しない。

## 公開URL

`https://harubaru74-collab.github.io/daily-news-topics/`
（リポジトリの Settings → Pages で「GitHub Actions」をソースに設定した後、初回のワークフロー実行後に有効になる）

## 日次ルーティンが変わったこと

深夜2:00の「daily-topics GitHub保存」ルーティンから、以下の作業が**不要になった**：
- アーカイブHTML全体の読み込み・組み立て直し
- Artifactツールでの再公開

代わりに必要なのは、従来通り `daily-topics/YYYY-MM-DD.md` を書いて `git push` するだけ。それだけで
GitHub Actionsが自動的にアーカイブページを更新する（pushから数十秒〜1分程度で反映される想定）。

朝7:00の配信トリガーが伝える「アーカイブページURL」も、旧Artifact URLからこのGitHub PagesのURLに
差し替えている。

## `scripts/build_archive.py` の変換ルール

`archive/BUILD-TOPICS.md` に記載されている変換ルール（Markdown → HTML）をそのままPythonで実装したもの。
新しい記事フォーマットが増えた場合は、このスクリプトも合わせて更新が必要。

### 既知のトレードオフ（正直な記録）

Claudeが手作業で組み立てていた頃と比べて、以下の点は自動化により**わずかに簡素化**されている：

1. **`issue-headline`（号の見出しキャッチコピー）**：以前はClaudeがその日で一番インパクトのある話題を軸に短く要約し直していたが、自動化後は**その日の1番目の記事の見出しをそのまま使う**（長い場合は20字で切って「…」を付ける）。多少長くなる・地味になることがある。
2. **`data-search`（検索用キーワード）**：以前は記事内容から関連キーワードを手で拾って詰め込んでいたが、自動化後は**各記事のジャンル名＋見出しをそのまま連結**したものになる。見出しに出てこない固有名詞・数値では検索にヒットしないことがある。
3. **表示崩れの監視**：以前は毎晩Claudeが目視で確認していたが、自動化後は無人。`scripts/build_archive.py`はパースに失敗した記事があっても処理を止めず、警告ログを出しつつ簡易表示にフォールバックする設計にしてあるが、完璧な保証ではない。

いずれも実害は小さいと判断して自動化を優先した。気になる崩れ・表記が見つかったら、`scripts/build_archive.py`の該当パーサーを直すか、教えてもらえれば都度調整する。

### 移行時に実際にハマった落とし穴（roumu-newsからの申し送り事項）

1. **viewportの付与忘れ**：`archive/shell-topics.html` はもともとArtifact用の「body断片」として作られていて、`<!DOCTYPE html>` `<head>` `<meta viewport>` を持たない（Artifactが公開時に自動付与してくれていたため）。GitHub Pagesではこれらが付与されないので、`scripts/build_archive.py`側で正式なHTML文書として組み立て直し、`<meta name="viewport" content="width=device-width, initial-scale=1">` を明示的に挿入している。これを忘れるとスマホでデスクトップ表示扱いされ、極端に縮小表示される。
2. **doc-comment内の"ISSUES_GO_HERE"文字列との二重置換**：`shell-topics.html` 冒頭のHTMLコメント（人間向けの説明文）の中に、プレースホルダーと同じ文字列 `<!-- ISSUES_GO_HERE -->` が例示として書かれている。置換前にこのコメント自体を取り除かないと、`str.replace()` がその出現箇所にもマッチしてしまい、記事が二重に差し込まれる（実際に一度この不具合を踏んだ）。`scripts/build_archive.py`では、正規表現で先頭のHTMLコメントを除去してから置換している。
3. **favicon**：Artifact公開時代は`favicon`パラメータで指定していた絵文字（💬）が、GitHub Pagesでは自動で付かない。`archive/shell-topics.html`の`<title>`直後に、絵文字を中央配置したインラインSVGの`<link rel="icon" href="data:image/svg+xml,...">`を直接埋め込んで対応している。背景を透過にせず、テーマカラー（`#f6f2e7`）の角丸背景（`rx="22"`）を敷いた上に絵文字を配置しないと、Android等のホーム画面ショートカットアイコンで絵文字がはみ出す。

## セットアップに必要な一回限りの手動作業

Claude側のツールにはGitHub Pagesを有効化するAPIがないため、これだけは人の手（またはGitHub上での操作）が必要：

1. リポジトリの **Settings → Pages** を開く
2. **Build and deployment → Source** を「**GitHub Actions**」に変更する
3. 保存すれば、次に`daily-topics/`が更新された時（＝次回の深夜2:00ルーティン、または`workflow_dispatch`での手動実行）から自動的に公開される

## ロールバック

もし何か問題が起きた場合、旧来のArtifact方式（`archive/BUILD-TOPICS.md`の手順）にいつでも戻せる。
`daily-topics/*.md`自体の保存場所・フォーマットは変わっていないので、データが失われることはない。
旧Artifact URL（`https://claude.ai/code/artifact/779ce592-a8dd-4301-b924-e01d354c34c6`）は、
この移行以降は更新を停止している（内容は移行時点のまま残る）。
