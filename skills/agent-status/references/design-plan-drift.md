# 設計: PLAN のドリフト検出とスタール通知（hook 案）

ステータス: **Phase 1 実装済み**（紐付け・導出・rollup・drift 併記・doctor）/ Phase 2 以降は設計のみ
対象: `agent-status` skill（観測側）＋ relay（イベント源）

## 0. 症状

`PLAN` セクションは `.agent-status/plan.json`（人手・エージェントが編集する台帳）をそのまま描く。
実際の作業状況は relay（`.relay/state.db`）と Herdr（pane / agent_status）にある。両者がずれる。

観測された典型例（nv-papers の実データ）:

- plan `A` = `working` の子 `A1/A2/A3` は relay `T2/T3/T4` が `running` → 一致。
- plan `C`（structured Unsupported diagnostics）= `pending` のまま。実際に着手済みなのか、
  まだ誰も触っていないのかが**台帳からは判別できない**（＝古いのか本当に pending なのか分からない）。
- 逆方向: plan が `working` のまま、relay に該当タスクが無い／担当 worker が `idle`/`stalled` → 誰も進めていない。

どちらも「**台帳が人間の手で更新されない限り腐る**」ことが原因で、hook で直すべきは
「状態の入力源を一本化すること」であって「plan.json を頑張って同期すること」ではない。

## 1. 原則: intent と observed を分ける

| 層 | 正本 | 内容 |
| --- | --- | --- |
| **intent** | `plan.json` | 何をやるつもりか（分解・担当・順序・親子）。**状態は持たない**（持っても宣言値扱い） |
| **observed** | relay `tasks` + `workers`、Herdr `pane.agent_status` | いま何が起きているか。状態の正本はこちら |

表示は **observed を優先**し、intent と食い違うときだけ差分を併記する。
これにより「plan.json を書き換え忘れた」ことが嘘の表示に直結しなくなる。

## 2. plan ↔ relay の対応付け（実装済み）

**リンクは relay 側のデータ**。`tasks.plan_id TEXT`（nullable、`idx_tasks_plan`）が唯一の実体で、
agent-status は `tasks.plan_id == plan item.id` の 1 条件だけで結合する。タイトル文字列は見ない。

付与の経路:

| 操作 | コマンド |
| --- | --- |
| 起票時に紐付ける | `relay task add "..." --plan A1` |
| 後付け・修正 | `relay task link T2 A1` / `relay task unlink T2` |
| 確認 | `relay task list`（`plan=` 列） / `relay task show <id>`（JSON） |

- 旧 DB は `src/db.ts` の `migrate()` が `ALTER TABLE tasks ADD COLUMN plan_id TEXT` で追従する
  （`SCHEMA` 実行は `migrate()` より先なので、索引は `migrate()` 側で作る）。
- **未知の plan_id**（plan.json に存在しない id）は `status doctor` が
  `unknown links T9->Z (no such plan item)` として報告する。relay は plan.json を知らないので関与しない
  （検証は plan を解釈できる側に置く）。
- plan item に複数タスクがぶら下がってよい（`relay_ids` は配列）。1 タスクは 1 plan item に属する。
- `plan.json` の `relay` 明示フィールドは**廃止**した（リンクの実体を 2 箇所に持たない）。

### 決定（採用）

- **リンクは `tasks.plan_id` に持つ**。付与は relay 側（`--plan` / `link`）で行うので
  **plan.json を編集する必要がない**（＝「人手更新が増えて腐る」という根本原因を増やさない）。
- 廃案: relay の title 先頭タグ（`U1-A:`）を正規表現で読む規約。理由は
  (1) タイトルを書き換えると壊れる、(2) 規則（program 付きタグ等）が増え続ける、
  (3) リンクが「表示側の推測」でしかない。データなら 1 箇所・1 条件で済む。
- 既存タスクのタイトルに残る `U1-A:` は**飾り**として残してよい（もう読まれない）。

## 3. 観測状態の導出（純関数・冪等）

```
observed(item) =
  running          -> working      (worker が居れば working、居なければ stalled候補)
  review           -> review
  queued           -> pending
  blocked_internal -> blocked
  blocked_human    -> blocked(human)
  failed           -> failed
```

親の rollup（これが「親が pending のまま」を構造的に潰す）:

- **relay 由来の子**（`source` が `relay` / `rollup`）だけを材料にする。優先順は
  `blocked → working → review → failed → pending → done`（先勝ち）。子が全部 `done` なら親も `done`。
- 観測付きの子が 1 つも無ければ、親は intent の `status` をそのまま出す（`source=intent`）。
  こうしないと、plan.json だけの repo で「親 done / 子 working」という手書きの意図が
  勝手に書き換わって偽の drift になる。
- 逆に 1 つでも relay リンクがあれば、親は宣言値ではなく実態で表示される。

## 4. スタール判定（idle の可視化）

relay 側に材料が既にある:

- `workers.last_progress_at` / `nudged_at`（`relay worker list` の `last-progress`）
- `tasks.lease_until`（lease が生きているか = 誰かが持っているか）
- `events` の `worker.stalled` / `task.lease_expired`
- `task_notes`（進捗メモの最終時刻）
- `countIdleSinceProgress()`（`session.idle` が progress 以降に何回出たか = 早期停止の兆候）
- Herdr の `pane.agent_status`（`working` / `idle`）

規則:

| 条件 | 表示 |
| --- | --- |
| observed=working かつ owner の最終進捗が `stall_after`（既定 10m）超 | `stalled 12m` |
| 上に加えて Herdr pane が `idle` | `idle 12m` |
| `session.idle` が progress 以降に 2 回以上 | `premature-stop?` |
| observed=pending かつ relay に running タスクがある | `drift: started` |
| observed=working かつ relay に紐付くタスクが無い | `unlinked!` |
| intent=pending / observed=working | `working ←pending` |
| intent=working / observed=pending | `pending ←working` |

しきい値は `config.json` の `plan.stall_after_minutes`（既定 10）／`plan.hint_idle` で調整。

## 5. hook 基盤の選択肢

relay はタスク状態の**単一ライター**で、`events` に id 連番の追記ログを持つ。
plan 側の導出は「relay のスナップショット＋plan の純関数」なので、**毎回計算しても軽い**。

| 案 | 仕組み | 長所 | 短所 |
| --- | --- | --- | --- |
| **A. 水位ポーリング（推奨・V1）** | `watch` の 5s tick で `events` の `MAX(id)` を読み、変化があれば導出を再計算 | relay 改修ゼロ。socket / plugin / 手動 sqlite など**どの経路の書き込みでも拾える**。壊れても表示が古いだけ | 最大 5s 遅延。常駐前提 |
| **B. relay post-transition hook（V2）** | `.relay/hooks.toml` に `on = ["task.claimed","task.submitted",...] / run = "status sync --once"` を足し、CLI がコミット後に fire-and-forget で起動 | ほぼ即時。イベントが正確 | relay 改修が必要。**必ず非同期・タイムアウト付き**（writer を止めない） |
| **C. SQLite trigger + outbox** | `tasks` UPDATE の trigger が `plan_outbox` に追記 | 経路非依存 | DDL を relay に足す。trigger からプロセスは起動できない |
| **D. Herdr hook** | pane / agent_status 遷移で発火 | スタール検出に効く | タスク状態は分からない。補助専用 |

**推奨: A を本体、B を後付けの高速化、D をスタール判定の補強。**
A だけで「plan が古い」問題は消える（表示側で observed を優先するため）。
B は遅延 5s が気になってから入れればよく、C は採らない（relay の DDL を汚す割に利点が薄い）。

## 6. 配置（何をどこに足すか）

```
.relay/state.db         # tasks.plan_id（実装済み・正本）
.agent-status/
  plan.json             # intent（既存。編集不要）
  config.json           # plan.stall_after_minutes（Phase 2 用）
```

- 導出は **in-process**。`plan-overlay.json` のような派生ファイルは作らない
  （`render` / `watch` が必要なときに plan.json + relay を読んで毎回導出する。軽い）。
- relay 側の追加は `tasks.plan_id` / `--plan` / `link` / `unlink` のみ（実装済み）。
- `watch` の tick は現在 `_config_stamp` で config 変更を検知している。Phase 3 でここに
  `events.MAX(id)` を足し、「relay が動いたときだけ」再導出する。

## 7. 表示（実装済み）

`PLAN` 行は既存の `status | title | [owner]` を保ったまま、状態ラベルに **effective** を出す:

```
PLAN (U1 — usability / productionization)
  working    usability / productionization program  [integrator]
    working    VRF-aware dataplane (RFC 0007)  [dataplane-coord]
      done       VRF RFC + 11 shared fixtures  [integrator]
      review     Rust VRF (T2)  [dataplane-rust]  ←working (T2)
    review     Containerlab native input (RFC 0008)  [control-coord]  ←working (T5)
    pending    structured Unsupported diagnostics  [integrator+control]
```

- 併記するのは**食い違いがある行だけ**（正常行は今まで通り 1 行）。
  書式は `←<declared> (<relay task ids>)` を黄色で行末に置く。
- 併記は幅に余裕が無いときは最初に落とす（本文が 6 桁未満になるなら出さない）。
- 状態ラベルは effective（=`observed` → 子の rollup → `declared`）。`source` は `--json` で見える。
- 現行の `PLAN (<title>)` 見出しは維持。

## 8. 失敗時の原則

1. hook は **writer を絶対に止めない**（fire-and-forget、timeout、失敗は `events` に `hook.failed` として記録）。
2. 導出は**冪等・純関数**（同じ DB + plan なら同じ結果）。
3. 欠損に強い: relay DB 無し / `events` テーブル無し / plan 無し → それぞれ今の表示へ縮退。
4. 書き戻しは**既定 off**。plan.json は人間の成果物なので、明示操作のときだけ触る。
5. 観測を intent に昇格させない（勝手に plan.json の status を書き換えない）。

## 9. 段階導入

- **Phase 1（表示だけ）— 実装済み**: `tasks.plan_id` で結合 → 導出＋rollup＋drift 併記。
  書き戻しなし。hook なし。agent-status 側だけで完結する。
  併せて relay 側に `relay task add --plan <plan-id>` / `task link` / `task unlink` を追加した
  （リンクの付与は起票・後付けの両方をコマンドで行う）。
- **Phase 2（スタール）**: `last_progress_at` / `agent_status` から `stalled` / `idle` を出す。
- **Phase 3（水位ポーリング）**: `watch` の tick に `events.MAX(id)` を組み込み、変化時のみ再導出。
- **Phase 4（任意）**: relay hook で即時化、plan.json への書き戻し（既定 off）。

## 10. 決定事項と残る論点

### 決定（確定）

1. plan.json の `status` は **intent として残す**（廃止して relay に一本化はしない）。
   表示は observed を優先し、食い違う行だけ差分を併記する。
2. 紐付けは **relay のデータ**（`tasks.plan_id`）。付与は relay 側の
   `relay task add --plan <plan-id>` / `relay task link <task> <plan-id>` で行う。
   タイトル文字列からの規約読みは**採らない**。
3. スタールのしきい値は **既定 10 分のまま**（チューニングは後回し）。
4. plan item の `relay` 明示フィールドは**廃止**（リンクの実体は 1 箇所）。

### 残る論点

1. スタールしきい値を program / task 単位で変えられるようにするか（既定 10 分は据え置きで後回し）。
2. リンク種別が増えたとき（RFC / issue 番号など）に `plan_id` 列を増やすか、
   `task_labels(task_id, kind, value)` に一般化するか。今は plan だけなので専用列で足りている。
3. `plan_id` は plan.json の `id` をそのまま受ける（program プレフィックスは付けない）。
   別 repo の plan を指す必要が出たら、そのときに修飾子を足す。
