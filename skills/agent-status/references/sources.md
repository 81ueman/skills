# データソース

`scripts/status` が読むのは次の4つ。互いに独立して失敗する（1つ読めなくても他は表示する）。

## 1. relay（タスクの正本）

- DB 探索順: config `relay.db` → `$AGENTCTL_DB` → `<repo>` から親方向に `.agentctl/state.db` を探索。
- 読み取り: Python stdlib `sqlite3` を `file:<path>?mode=ro`（read-only）で開く。
  失敗時は `sqlite3 -readonly -json` CLI にフォールバック。**書き込みは一切しない。**
- 使うテーブルと列（relay の `src/schema.ts` 準拠）:

  | テーブル | 列 |
  | --- | --- |
  | `tasks` | `id, title, state, priority, role, assignee, parent_task_id, updated_at` |
  | `workers` | `id, role, state, current_task_id, generation, last_progress_at` |

- task state: `queued running review done blocked_internal blocked_human failed`
- worker state: `starting idle working waiting_input stalled dead`
- 表示順（残り）: `running → queued → review → blocked_human → blocked_internal → failed`、
  同 state 内は priority 降順。`done` は完了欄。
- 階層: `parent_task_id` があれば親子を **ツリー表示**（子は 2 スペース/段でインデント）。
  兄弟は上記の state/priority 順。親が存在しない孤児や循環参照は depth 0 に落として必ず表示する。
  `done` の子も所属段は保たれる（残り/完了のセクションをまたいでもインデントは維持）。

将来 relay が `agentctl status --json` などを公開したら、それを優先する実装に差し替える。

## 2. Herdr（pane / agent のライブ状態）

- `HERDR_ENV=1` のときだけ有効。`herdr pane list --workspace <ws>` を対象 ws ごとに実行。
- JSON の `result.panes[]` から使うフィールド:
  `pane_id, agent, agent_status, terminal_title_stripped, cwd, workspace_id, tab_id, focused`
- 対象 ws の決定順:
  1. `--workspace`（複数可）
  2. config `herdr.workspaces`
  3. `$HERDR_WORKSPACE_ID`
- `herdr.cwd_match = true`（既定）なら、集めた pane のうち `cwd` が `<repo>` 配下のものだけに絞る。
- `herdr.show_shells = false`（既定）なら、`agent` を持たない pane（シェルやコマンド実行中の pane）は除外する。
  これによりダッシュボード自身の pane（エージェント無し）が `unknown` として混ざらない。`true` で全 pane を表示。
- 追跡中の status pane（`.agent-status/status-pane`）は常に除外する。
- pane 確保・停止に使うコマンド:
  `herdr pane split --pane <id> --direction right|down --cwd <dir> --no-focus` /
  `herdr pane run <id> <cmd>` / `herdr pane get <id>` / `herdr pane close <id>`

## 3. git（KPI）

- `git log -1 --format='%h %s'` / `git rev-parse --abbrev-ref HEAD` / `git status --porcelain`
- dirty 件数は config `kpi.exclude` に部分一致するパスを除いて数える
  （既定で `README.md catalog.json notes/ papers/ summaries/ .agent-status/` を除外）。

## 4. plan（フォールバック）

- config `plan.path`（既定 `.agent-status/plan.json`）。relay と併記可能。
- スキーマは [config.md](config.md) を参照。
