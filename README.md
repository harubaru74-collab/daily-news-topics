# daily-news-topics（時事おしゃべりネタ帳）

労務ニュース（[roumu-news](https://github.com/harubaru74-collab/roumu-news)）とは別ジャンルの、幅広い一般ニュース＋世間の反応を毎日まとめるリポジトリ。

転職活動の面接や日常会話で「〇〇のニュース、どう思う？」と聞かれたときに、事実を知ってるだけでなく自分なりの意見を持って答えられるようにすることが目的。単なる事実の要約ではなく、世間の反応（賛否）まで拾って論点を整理し、実際に聞かれたときに使える一言コメント案まで用意する。

## 公開ページ

`https://harubaru74-collab.github.io/daily-news-topics/`

## ディレクトリ構成

```
daily-topics/
  YYYY-MM-DD.md   各日のまとめ
archive/
  shell-topics.html   アーカイブページのデザイン土台
  BUILD-TOPICS.md     Markdown→HTML変換ルール（仕様書）
  AUTOBUILD.md        自動ビルドの仕組み・セットアップ手順
scripts/
  build_archive.py    docs/index.html を組み立てるビルドスクリプト（AI不使用）
docs/
  index.html           GitHub Pagesが公開する実体（自動生成、手動編集しない）
```

## 自動実行について

毎日深夜2:00（JST）に自動収集・保存し、朝7:00（JST）に通知する2トリガー体制で運用している。詳細は [`ROUTINE-TOPICS.md`](./ROUTINE-TOPICS.md) を参照。アーカイブページの自動公開の仕組みは [`archive/AUTOBUILD.md`](./archive/AUTOBUILD.md) を参照。

## 移行の経緯

もともとは `roumu-news` リポジトリの `claude/daily-news-topics-routine-ak81mg` ブランチに間借りする形で運用していたが、2026-08-25にアーカイブページをGitHub Pagesへ移行するタイミングで、このリポジトリとして独立させた（GitHub Pagesは1リポジトリにつき1サイトしか持てないため）。
