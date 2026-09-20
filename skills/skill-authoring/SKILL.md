---
name: skill-authoring
description: 新しい Agent Skill を作成・追加・編集するときに使う。管理リポジトリ（~/ghq/github.com/81ueman/skills）に skills/<name>/ として実体を置き、SKILL.md の frontmatter を整え、README を更新して commit/push し、APM（apm update -g）で ~/.agents/skills に展開する。「skill を作って」「スキルを追加」「新しいスキルがほしい」「skill を編集」などで使う。
---

# スキル作成（skill-authoring）

新規スキルをこの管理リポジトリで一元管理するための手順書。
**実体はリポジトリ側**に置き、各エージェントの探索ディレクトリへは APM でコピー配備する。

## 前提知識

- 管理リポジトリ: `~/ghq/github.com/81ueman/skills`（remote: `81ueman/skills`）
- 実体の置き場: `<repo>/skills/<name>/`
- 配備ツール: [APM](https://microsoft.github.io/apm/)（`brew install apm`）
- 初回配備: `apm install -g --target agent-skills 81ueman/skills`
- 更新配備: `apm update -g`（commit/push 後に実行）
- 配備先: `~/.agents/skills/<name>/`（Agent Skills 標準。opencode は `~/.agents/`・`~/.claude/`・`~/.config/opencode/` を探索する）
- 外部から入れたスキルは `npx skills` と `~/.agents/.skill-lock.json` が管理する。**このリポジトリには入れない**

## 手順

### 0. 衝突確認

`ls ~/.agents/skills` と `~/.agents/.skill-lock.json` を見て、使う名前が既存スキルと衝突しないか確認する。
特に外部スキル（`herdr` / `find-skills` / `code-review` / `hunk-review` / `architecture-decision-records` / `grill-me`）や relay の `agent-worker` とは同名にしない。

### 1. 名前を決める

- 形式: `^[a-z][a-z0-9._-]*$`（英小文字始まり、ハイフン可）
- **ディレクトリ名と frontmatter の `name` を同じ**にする
- パスがそのままスキルIDになるので日本語は使わない

### 2. 雛形を作る

```sh
~/.agents/skills/skill-authoring/scripts/new-skill.sh <name>
```

`<repo>/skills/<name>/SKILL.md` を作成する。手動で行う場合:

```sh
REPO="$HOME/ghq/github.com/81ueman/skills"
mkdir -p "$REPO/skills/<name>"
cp "$REPO/skills/skill-authoring/templates/skill-template.md" "$REPO/skills/<name>/SKILL.md"
```

### 3. SKILL.md を書く

frontmatter は必須。**`description` が最重要**で、エージェントはこれだけを見てロードするか判断する。

| フィールド | 必須 | 説明 |
| --- | --- | --- |
| `name` | ○ | ディレクトリ名と同じ |
| `description` | ○ | 「何を・いつ使うか」。ユーザーが言いそうな発火語を含める |
| `slash` | – | `true` で手動 `/名前` 起動に対応 |
| `autoinvoke` | – | `false` で description による自動起動を無効化 |

本文には手順・判断基準・アンチパターンを具体的に書く。長い詳細は `references/` に逃がし、SKILL.md から相対リンクで参照する。

### 4. 補助ファイルを置く（任意）

`references/`（詳細）、`templates/`（雛形）、`scripts/`（補助コマンド）などは同ディレクトリ内に置く。SKILL.md からの参照を忘れない。

### 5. README を更新

`<repo>/README.md` の構成ツリーとスキル一覧の表に 1 行追加する。

### 6. commit & push

```sh
cd "$HOME/ghq/github.com/81ueman/skills"
git add skills/<name> README.md
git commit -m "Add <name> skill"
git push
```

APM は git ref を固定して配備するため、**push しないと配備に反映されない**。

### 7. 配備（APM）

```sh
apm update -g
```

`~/.agents/skills/<name>/` に実体がコピーされる。

### 8. 動作確認

**新しい opencode セッション**を開く（既存セッションは一覧をキャッシュしている）。available skills に表示され、`description` が意図どおりなら OK。
表示されない場合は次を確認する:

- `SKILL.md` がスキル直下にあるか
- frontmatter が壊れていないか（壊れていると**無言でスキップ**される）
- 配備されているか（`ls ~/.agents/skills/<name>`。APM 管理なので symlink ではなく実体）
- push 済みで `apm update -g` を実行したか

## アンチパターン

- `~/.agents/skills/<name>/` を直接編集する（APM 管理下。次回の `apm update` で上書きされる。実体は必ずリポジトリ側で編集）
- `~/.agents/skills/<name>` を symlink で張る（APM と二重管理になる）
- push せずに `apm update -g` する（古い commit のまま）
- 補助ファイルを `SKILL.md` という名前で置く（→ opencode は `**/SKILL.md` を再帰的に拾うため、**別スキルとして誤認識される**。雛形は `skill-template.md` のように別名にする）
- ディレクトリ名と frontmatter `name` が不一致（→ 認識されない・IDがずれる）
- `description` が曖昧（→ 発火しない）
- `.skill-lock.json` を手で編集する（外部スキル管理用）
- 既存の外部スキルや relay の `agent-worker` と同名にする
- README を更新し忘れる

## チェックリスト

- [ ] 名前が既存スキルと衝突しない
- [ ] `skills/<name>/SKILL.md` がある
- [ ] frontmatter に `name` と `description` がある
- [ ] 名前がディレクトリと frontmatter で一致している
- [ ] README を更新した
- [ ] commit / push した
- [ ] `apm update -g` した
- [ ] 新セッションで表示を確認した

## 参考

- 雛形: [templates/skill-template.md](templates/skill-template.md)
- 自動化: [scripts/new-skill.sh](scripts/new-skill.sh)
- APM: https://microsoft.github.io/apm/
