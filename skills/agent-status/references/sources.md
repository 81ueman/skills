# データソース

## 1. Relay（必須・read-only・正本）

`<repo>/.relay/state.db` を **`mode=ro`** で開く。書き込み・`relay` コマンド実行は一切しない。

| テーブル | 読む列 |
| --- | --- |
| `tasks` | `id, title, state, priority, role, assignee, parent_task_id, updated_at` |
| `workers` | `id, role, state, current_task_id, generation, last_progress_at`（+ `quiet_until, quiet_reason` / `retired_at` があれば） |
| `worker_runtimes` | `worker_id, generation, state, relay_owned, workspace_id, tab_id, pane_id, runtime_id, session_id, created_at` |
| `messages` | `recipient, state`（未読数だけ。本文は読まない） |
| `task_notes` | `blocked_human` / `blocked_internal` の最新理由（ATTENTION 用） |

- task state: `queued running review done blocked_internal blocked_human failed`
- worker state: `starting idle working waiting_input stalled dead`
- `retired_at IS NOT NULL` の worker は表示しない。
- 列の有無は `PRAGMA table_info` で guard する（古い Relay DB でも動く）。

### 導出（agent-status の表示ラベル、DB には書かない）

- **task tree**: `tasks.parent_task_id` で親子に並べる。work decomposition であり worker の上下関係ではない。
  active → priority 降順 → id 固定。全子孫が done の subtree は 1 行に畳む。
- **worker-centric join**: `WORKERS` は relay worker 一覧が骨格。**1 worker = 1 row**。current runtime は
  `worker.generation` に一致する `worker_runtimes` 行（無ければ pane なし。古い世代で代用しない）。
  generation / pane / exec はその current runtime のもの。古い世代は `--runtime-history` でのみ列挙する。
- **exec label**（Herdr 実行状態。Relay state とは別列）:
  - Relay state が `starting` → `starting`
  - Herdr が `working` → `busy`
  - Relay の `quiet_until > now` → `quiet <残り>`（意図的な bounded idle）
  - Relay state が `working`＋タスク保持＋Herdr idle → `!idle`（unexpected idle）
  - pane なし / Herdr off → `unavailable`
  - それ以外 → `idle`
- **ATTENTION**（derived のみ）: unexpected idle / `stalled` / `dead` / starting 長期化 /
  unclaimable（role を担う worker が居ない queued）/ `blocked_*` / `failed` / 未読メッセージ /
  runtime pane を持たない worker / relay-owned の古い runtime で cleanup overdue（`cleanup_after <= now`）。
- **task progress**: `done/total` 件数と state 内訳。git は progress の正本にしない。

## 2. Herdr（実行テレメトリ）

- `HERDR_ENV=1` のときだけ有効。`herdr pane list --workspace <ws>` を対象 ws ごとに実行。
- 対象 ws は `herdr.workspaces` ∪ relay の `worker_runtimes.workspace_id`（自動追従）。
- `herdr.cwd_match` で `<repo>` 配下に絞る。ダッシュボード自身の pane は常に除外。
- Relay 管理外の pane（シェル等）は**表示しない**。WORKERS は Relay worker のみを骨格にし、unmanaged pane は worker row を作らない。
- 各 pane から `agent_status`（`working` / `idle` / `done` / `blocked` / `unknown`）を実行状態として読む。
  **これは work state ではなく実行テレメトリ**。worker は current runtime（`worker.generation` 一致）の `pane_id` で対応付ける。
- pane id は OSC8 リンク（`herdr.links`）。Ctrl+click は Herdr プラグイン（`herdr-plugin/`）が
  socket `pane.focus` に回す。

## 3. git（補助 KPI）

- `branch` / `HEAD`（`<sha> <subject>`）/ dirty 件数（`kpi.exclude` で除外）。
- task progress の正本ではない。表示専用。

## 4. `status doctor`

```
repo / config / HERDR_ENV
relay db         OK <path> | (not found - run: relay init)
tasks / workers / current runtimes
runtime links    <pane を持つ current runtime の worker>/<worker 数>
stale runtimes   <stale/dead の数>
daemon/socket    OK <sock> | (no socket)
herdr            OK (<n> panes) | off
```

`plan` / `drift` / `unlinked` / `unknown plan ids` は**廃止**。
