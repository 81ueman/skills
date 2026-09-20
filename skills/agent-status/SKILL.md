---
name: agent-status
description: Herdr上で複数エージェントが並行作業しているときのライブ進捗ダッシュボードを、呼び出し中のpaneの隣に表示する。relay（SQLite が正本）のタスク台帳とHerdrのpane/agent状態、gitのKPIを集約し、残りタスク・完了タスク・worker状態をANSIで自動更新表示する。「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスク一覧」「タスクの進み具合」「agent-status」などで使う。
slash: true
---

# agent-status

## 概要

複数エージェント（Herdr の別 pane / relay worker）にまたがる作業の進捗を 1 画面に集約し、
**残りタスク・完了タスク・各 worker/agent の状態**を一目で見えるようにする。常駐はせず、
明示的に呼び出したときだけ Herdr ペインを 1 枚開いて自動更新する。

タスクの正本は **relay（SQLite: `<repo>/.relay/state.db`）**。
Herdr は pane/agent のライブ状態、git は補助 KPI を提供する。本スキルは表示専用で、
タスクの追加・claim・submit などは行わない（それは `relay` CLI の仕事）。
表示中に `.agent-status/config.json` を編集すると次の更新で反映される（pane 再起動不要）。

## いつ使うか

- 統括エージェントとして複数の部下へ委譲しており、残タスク/完了タスクを俯瞰したいとき
- 単独作業でも、自分の pane の隣に進捗を出しておきたいとき
- 「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスクは」と言われたとき
- 手動起動: `/agent-status`

## 前提

- Herdr 内で実行していること（`HERDR_ENV=1`）。ペイン表示は Herdr 必須。
- タスク台帳は relay が動いているリポジトリの `<repo>/.relay/state.db`。
  DB は **read-only** でしか読まない（WAL への書き込みをしない）。
- relay が無いリポジトリでは `.agent-status/plan.json`（手書き）にフォールバックする。
  どちらも無ければタスク欄は空表示になる（推測で埋めない）。
- pane id の **Ctrl+click 移動**を使うには、Herdr プラグインを一度 link しておく（任意）:

  ```bash
  herdr plugin link ~/.agents/skills/agent-status/herdr-plugin   # プラグイン id: agent-status.pane-links
  ```

  link しなくても階層表示は動く（pane id はリンクとして描画されるが、Ctrl+click は Herdr に拾われない）。

## 手順

入口は `scripts/status`（Python3 stdlib のみ）。スキルディレクトリからの相対パスで呼ぶ。

1. まず検出状態を確認する（どのソースが使われるか）:

   ```bash
   python3 scripts/status doctor --repo "$PWD"
   ```

2. 呼び出し元 pane の隣にライブ表示を出す:

   ```bash
   python3 scripts/status show --repo "$PWD"
   # 統括エージェントの pane を指定してその隣に出す場合
   python3 scripts/status show --pane w52:p2M --direction right --repo "$PWD"
   ```

   - 既定は「呼び出し元 pane の右」。既存の status pane があれば再利用する。
   - 対象 workspace を明示する場合は `--workspace w50 --workspace w61`（複数可）。
   - 既定の対象は現在の `$HERDR_WORKSPACE_ID` かつ `<repo>` 配下の cwd を持つ pane。

3. 止めるとき:

   ```bash
   python3 scripts/status hide --repo "$PWD"
   ```

4. pane を開かず 1 回だけ見る / 機械可読が欲しいとき:

   ```bash
   python3 scripts/status render --repo "$PWD"
   python3 scripts/status render --json --repo "$PWD"
   python3 scripts/status watch --repo "$PWD" --interval 5   # pane 内で直接回す用
   ```

## 判断基準

| 条件 | どうする |
| --- | --- |
| 統括 pane の隣に出したい | `status show --pane <統括pane>` |
| 自分（呼び出し元）の隣でよい | `status show` |
| w50/w61 など複数 workspace を跨ぐ | `status show --workspace w50 --workspace w61` |
| relay がまだ無いリポジトリ | `.agent-status/plan.json` を置く（[references/config.md](references/config.md) のスキーマ） |
| 表示を細かく変えたい（KPI 追加・除外） | `.agent-status/config.json` を編集 |
| relay を読めているか不安 | `status doctor` で DB / 行数を確認 |
| タスクを進めたい | 本スキルではなく `relay next/note/submit`（`agent-worker` skill） |

## 表示の読み方

- `tasks done/total [####----]` … relay の `done` 件数と全件数、プログレスバー。
- `REMAINING` … `running → queued → review → blocked_* → failed` の順。各行は `state / id / title / [assignee]`。
  relay の `parent_task_id` があれば親子をツリー表示（子はインデント）。
- `DONE (n)` … 完了タスク（最新 30 件）。階層があれば同じ段でインデント表示。
- `PLAN` … plan.json の台帳。`parent` があればツリー表示。
- `RELAY WORKERS` … `relay` の worker 状態と最終進捗からの経過時間。
- `HERDR PANES` … `workspace → tab → pane` の階層で表示。pane ごとの `agent_status`（working/idle/blocked/unknown）、`*` はフォーカス中。
  workspace / tab が複数あるときだけ見出し（tab はラベル付き）を出し、pane はその下にインデントされる。
  エージェントの居ない pane（シェル等）とダッシュボード自身の pane は既定で非表示（`herdr.show_shells` で表示）。
  pane id を **Ctrl+click** するとその pane にフォーカスが移る（要プラグイン link、`herdr.links=false` で無効化）。
  pane id はリンクとして下線付きで表示し、末尾に `Ctrl+click a pane id → focus that pane` のヒント行を出す。
- `sources` … relay / herdr / plan のどれを採用したか。

## アンチパターン

- `HERDR_ENV != 1` で `status show` を呼ぶ（ペインを作れない。`render` を使う）
- relay DB を書き込みモードで開く・`relay` のタスクを本スキルから更新する（表示専用）
- relay が無いのにタスク欄を推測で埋める（空のまま出す）
- 自分の作った status pane 以外を `hide` で閉じる（本スキルは追跡中の pane だけを閉じる）
- 常駐させるために daemon 化する（常時起動はしない。必要なときだけ `show`/`hide`）

## 参考

- データソースの詳細: [references/sources.md](references/sources.md)
- config スキーマと plan フォーマット: [references/config.md](references/config.md)
- 設定雛形: [templates/config.json](templates/config.json)
- Ctrl+click で pane へ移動する Herdr プラグイン: [herdr-plugin/](herdr-plugin/)（`[[link_handlers]]` + socket `pane.focus`）
- relay 本体: `~/ghq/github.com/81ueman/relay`（SQLite が正本）
