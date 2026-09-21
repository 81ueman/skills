# skills

自分で作成した Agent Skill をまとめて管理するリポジトリ。

配布・配備は [APM (Agent Package Manager)](https://microsoft.github.io/apm/) で行う。
実体はこのリポジトリの `skills/<name>/` に置き、`apm install` で各エージェントの
スキル探索ディレクトリへ展開する（APM はコピー配備。git ref を `~/.apm/apm.lock.yaml` に固定する）。

## 構成

```
skills/
  agent-status/         `relay dashboard` を pane の隣に出す薄いラッパースキル
  d2-diagrams/          D2（Terrastruct D2）で図を描くスキル
  diagram-tool-choice/  d2 と Mermaid のどちらを使うか判断する入口スキル
  mermaid-diagrams/     Mermaid で図を描くスキル
  skill-authoring/      新しいスキルを作成・追加する手順スキル
  voice-check/          音声入力の文字起こしを日本語として整形・確認するスキル
```

| スキル | 説明 |
| --- | --- |
| `agent-status` | relay 本体の `relay dashboard` を pane の隣に出す薄いラッパー（実体は relay、fallback なし） |
| `diagram-tool-choice` | 図を描く前に d2 / Mermaid を判断軸の表で選び、対応するスキルへ誘導する |
| `d2-diagrams` | d2 の CLI、レイアウトエンジン（dagre/elk/tala）、記法、テンプレート |
| `mermaid-diagrams` | Mermaid の CLI（mmdc / mermaid-ascii）、記法、テンプレート |
| `skill-authoring` | 新規スキル作成の手順（実体の置き場・frontmatter・APM 展開・commit/push） |
| `voice-check` | 音声入力の崩れを検知し、自然な日本語に整えて実行前に確認する |

`diagram-tool-choice` から `d2-diagrams` / `mermaid-diagrams` に分岐する 3 点セットで使う。

## セットアップ（APM）

```sh
brew install apm
```

このリポジトリのスキルをグローバルへ展開する。

```sh
apm install -g --target agent-skills 81ueman/skills
```

- `~/.agents/skills/<name>/` に実体がコピーされる（`agent-skills` は Agent Skills 標準の共有ディレクトリ）
- OpenCode は `~/.agents/skills/`（互換）・`~/.config/opencode/skills/`（ネイティブ）・`~/.claude/skills/` を探索するため、`agent-skills` だけで認識される
- Claude Code など他のハーネスにも配る場合は target を足す（例: `--target agent-skills,claude`）
- グローバル側の台帳は `~/.apm/apm.yml` と `~/.apm/apm.lock.yaml`

更新（push 済みの最新を取り込む）:

```sh
apm update -g
```

## 他リポジトリが実体を持つスキル

プロダクト側のリポジトリが正本のスキルも、そのリポジトリの APM パッケージとして
別途 install する。クロスリポジトリの symlink はコミットしない方針を維持する。

| スキル | 実体 | 展開 |
| --- | --- | --- |
| `agent-worker` | `relay` リポジトリの `skills/agent-worker/` | `apm install -g --target agent-skills 81ueman/relay` |

## 外部からインストールしたスキルとの違い

`~/.agents/skills/` には外部リポジトリから導入したスキルも同居している。それらは
`npx skills` と `~/.agents/.skill-lock.json` が管理し、更新はインストール元に従う。
APM が管理するのは `~/.apm/apm.yml` に載ったスキル（自分で作成したもの＋relay）だけ。

## 手順書

新しいスキルの作り方は [skills/skill-authoring/](skills/skill-authoring/SKILL.md) を参照。
