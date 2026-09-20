# 設計: PLAN のドリフト検出とスタール通知（hook 案）

ステータス: **設計のみ（未実装）** / 対象: `agent-status` skill（観測側）＋ relay（イベント源）

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

## 2. plan ↔ relay の対応付け

優先順で解決する（上から試す）:

1. 明示: plan item に `"relay": "T5"`（単一）または `"relay": ["T5","T6"]`（複数）。
2. 規約: relay の title 先頭タグ ↔ plan `id`。**既に運用されている**（例: plan `A` ↔ `T1: "U1-A: VRF-aware dataplane..."`）。
   規則: `^\s*U1-<id>\b` あるいは `^<id>:` を relay title / description から拾う。
3. 明示 `relay: false` → 紐付けない（純粋な intent 行として `(intent)` 表示）。
4. 未解決は unlinked として「relay に実体なし」を明示（ペナルティにはしない）。

### 決定（採用）

- **併用（明示優先＋規約フォールバック）**。どちらか一方に寄せない。
- リンクの付与は **relay 側で自動化**する: `relay task add "..." --plan A` で title 先頭に
  `U1-A:` を自動付与（既存のタグ運用と同型）。`--parent` と同様の小改修で済む。
  - タスク起票時に plan id を渡すだけなので **plan.json を編集する必要がない**
    （＝「人手更新が増えて腐る」という根本原因を増やさない）。
  - 書き忘れても規約側で拾えるため、リンクが切れても致命的にならない。
  - plan.json への手書き `"relay": "T5"` は、1 項目に複数タスクを束ねる／
    規約に乗らない例外的な対応が必要なときだけ使う（任意機能）。

`config.json` に `plan.link: { field: "relay", tag: "^U1-(?P<id>[A-Z0-9]+)" }` の形で既定を持たせる。

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

- 子に `working`/`blocked` が 1 つでもあれば親は `working`（`blocked` が優勢なら `blocked`）。
- 子が全部 `done` なら親は `done`（relay に親タスクが無くても成立）。
- 観測が無い item は intent の `status` をそのまま使う（後方互換）。

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
.agent-status/
  plan.json            # intent（既存）
  plan-overlay.json    # 派生キャッシュ（生成物・gitignore 推奨）
  config.json          # plan.link / plan.stall_after_minutes を追加
```

- `scripts/status sync [--once] [--plan] [--dry-run]`
  - relay スナップショット → 導出 → `plan-overlay.json` を書く。
  - `--plan` を付けたときだけ plan.json へ**書き戻す**（既定 off、`--dry-run` で差分表示）。
- `render` / `watch` は **read-only のまま** `plan-overlay.json` を読む（描画は今まで通り軽い）。
- `watch` の tick は現在 `_config_stamp` で config 変更を検知している。ここに
  `events.MAX(id)` を足して「変化したときだけ sync 相当を再計算」する。
- 導出関数は独立モジュール（`scripts/plan_state.py` 等）にして、relay 無しでも
  plan だけで縮退動作できるようにする（relay DB が無ければ今の表示に戻る）。

## 7. 表示

`PLAN` 行は既存の `status | title | [owner]` を保ったまま、状態ラベルに観測を出す:

```
PLAN (U1 — usability / productionization)
  working    usability / productionization program  [integrator]
    working    VRF-aware dataplane (RFC 0007)  [dataplane-coord]
      done       VRF RFC + 11 shared fixtures  [integrator]
      working    Rust VRF (T2)  [dataplane-rust]
    working    Containerlab native input (RFC 0008)  [control-coord]
    pending    structured Unsupported diagnostics  [integrator]   working ←pending
    pending    one-command workflow (nv CLI)  [integrator]        stale 32m
```

- 併記するのは**食い違いがある行だけ**（正常行は今まで通り 1 行）。
- 併記は行末に置き、幅に余裕が無いときは最初に落とす（既存の幅対応に乗せる）。
- スタール・drift がある行だけ色を変える（`stalled` 赤 / `drift` 黄）。
- 現行の `PLAN (<title>)` 見出しは維持。

## 8. 失敗時の原則

1. hook は **writer を絶対に止めない**（fire-and-forget、timeout、失敗は `events` に `hook.failed` として記録）。
2. 導出は**冪等・純関数**（同じ DB + plan なら同じ結果）。
3. 欠損に強い: relay DB 無し / `events` テーブル無し / plan 無し → それぞれ今の表示へ縮退。
4. 書き戻しは**既定 off**。plan.json は人間の成果物なので、明示操作のときだけ触る。
5. 観測を intent に昇格させない（勝手に plan.json の status を書き換えない）。

## 9. 段階導入

- **Phase 1（表示だけ）**: 紐付け（明示＋規約）→ 導出＋rollup＋drift 併記。書き戻しなし。hook なし。
  agent-status 側だけで完結する。← ここだけで user の困りごとは解ける
  - 並行して relay 側に `relay task add --plan <id>`（title へ `U1-<id>:` 自動付与）を足す。
    これは新しい作業の書き忘れを防ぐためのもので、Phase 1 の表示には必須ではない。
- **Phase 2（スタール）**: `last_progress_at` / `agent_status` から `stalled` / `idle` を出す。
- **Phase 3（水位ポーリング）**: `watch` の tick に `events.MAX(id)` を組み込み、変化時のみ再導出。
- **Phase 4（任意）**: relay hook で即時化、`status sync --plan` で書き戻し。

## 10. 決定事項と残る論点

### 決定（確定）

1. plan.json の `status` は **intent として残す**（廃止して relay に一本化はしない）。
   表示は observed を優先し、食い違う行だけ差分を併記する。
2. 紐付けは **併用**: 明示 `relay` フィールド優先 → タグ規約 `U1-<id>:` フォールバック。
   付与は **relay 側で自動化**（`relay task add --plan <id>`）。
3. スタールのしきい値は **既定 10 分のまま**（チューニングは後回し）。

### 残る論点

1. スタールしきい値を program / task 単位で変えられるようにするか（既定 10 分は据え置きで後回し）。
2. `plan-overlay.json` を持つか、`watch` のプロセス内メモリだけにするか
   （外部から `render` したときに古い overlay を拾わない注意）。
3. `relay task add --plan <id>` のタグ書式を `U1-<id>:` に固定してよいか
   （program 名が増えたときの命名。`--plan` は program プレフィックス込みで受けるか、id だけにするか）。
