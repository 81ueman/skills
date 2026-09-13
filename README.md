# skills

自分で作成した Agent Skill をまとめて管理するリポジトリ。

`~/.agents/skills/` などに置いたスキルの実体をここに移し、各エージェントのスキル探索ディレクトリから
シンボリックリンクで参照する。編集は常にこのリポジトリ側で行う。

## 構成

```
skills/
  d2-diagrams/          D2（Terrastruct D2）で図を描くスキル
  diagram-tool-choice/  d2 と Mermaid のどちらを使うか判断する入口スキル
  mermaid-diagrams/     Mermaid で図を描くスキル
  voice-check/          音声入力の文字起こしを日本語として整形・確認するスキル
```

| スキル | 説明 |
| --- | --- |
| `diagram-tool-choice` | 図を描く前に d2 / Mermaid を判断軸の表で選び、対応するスキルへ誘導する |
| `d2-diagrams` | d2 の CLI、レイアウトエンジン（dagre/elk/tala）、記法、テンプレート |
| `mermaid-diagrams` | Mermaid の CLI（mmdc / mermaid-ascii）、記法、テンプレート |
| `voice-check` | 音声入力の崩れを検知し、自然な日本語に整えて実行前に確認する |

`diagram-tool-choice` から `d2-diagrams` / `mermaid-diagrams` に分岐する 3 点セットで使う。

## セットアップ

スキルの実体を各エージェントの探索ディレクトリへシンボリックリンクする。

```sh
REPO="$HOME/ghq/github.com/81ueman/skills"   # このリポジトリのパスに合わせる

mkdir -p "$HOME/.agents/skills"
for s in d2-diagrams diagram-tool-choice mermaid-diagrams voice-check; do
  rm -rf "$HOME/.agents/skills/$s"
  ln -s "$REPO/skills/$s" "$HOME/.agents/skills/$s"
done
```

OpenCode は `~/.agents/`・`~/.claude/`・`~/.config/opencode/` のスキルを探索するため、
上記リンクだけで認識される。Claude Code からも使いたい場合は `~/.claude/skills/` にも同様に貼る。

```sh
for s in d2-diagrams diagram-tool-choice mermaid-diagrams voice-check; do
  rm -rf "$HOME/.claude/skills/$s"
  ln -s "$REPO/skills/$s" "$HOME/.claude/skills/$s"
done
```

## 外部からインストールしたスキルとの違い

`~/.agents/skills/` には外部リポジトリから導入したスキルも同居している。それらは
`~/.agents/.skill-lock.json` で管理され、更新はインストール元に従う。このリポジトリで管理するのは
自分で作成したスキルだけとし、二重管理を避ける。
