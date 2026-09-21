---
name: agent-status
description: Relay control plane の read-only ダッシュボードを、呼び出し中の pane の隣に表示する。実体は relay 本体の `relay dashboard`。task tree / worker（current runtime を重ねる）/ attention を、Herdr の実行状態つきで自動更新する。「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスク一覧」「タスクの進み具合」「agent-status」などで使う。
slash: true
---

# agent-status

Relay の read-only ダッシュボードを、呼び出し元 pane の隣に出すだけの薄いスキル。

```
agent-status = relay dashboard --show
```

**実装は relay 本体にある**（`relay dashboard`、`src/dashboard/`）。このスキルはその起動だけを行う。
Python スクリプト・DB の直接解釈・独自の描画・Herdr の直接操作は持たない（重複と drift を防ぐ）。

## いつ使うか

- 複数 worker にまたがる作業の残タスク/完了/attention を俯瞰したいとき
- 自分の pane の隣に進捗を出しておきたいとき
- 「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスクは」と言われたとき
- 手動起動: `/agent-status`

## 手順

1. 呼び出し元 pane の隣にライブ表示を出す:

   ```bash
   relay dashboard --show
   ```

   - 既存の dashboard pane があれば**再利用**する（移すときは `--hide` → `--show`）。
   - 独立 tab にしたいときは `relay dashboard --show --tab`（他 pane を分割しない）。
   - 特定の pane の隣に出したいときは `relay dashboard --show --pane w52:p2M --direction right`。

2. 止める / 一回だけ見る:

   ```bash
   relay dashboard --hide
   relay dashboard
   relay dashboard --json
   ```

3. 表示が怪しいとき:

   ```bash
   relay dashboard --doctor   # relay db / socket / herdr / tasks / workers / runtimes
   ```

## 前提

- Herdr 内で実行していること（`HERDR_ENV=1`）。ペイン表示は Herdr 必須。
- Relay の control plane が存在すること: `<repo>/.relay/state.db`（`relay init`）。
- `relay` が PATH にあること（`bun link`）。無ければ `bun <relay>/src/cli.ts dashboard`。
- pane id の **Ctrl+click 移動**は relay 同梱の Herdr プラグインで有効になる（任意）:

  ```bash
  herdr plugin link "$(pwd)/integrations/herdr"   # relay checkout で。id: relay.pane-links
  ```

## 表示の読み方

- ヘッダ: `relay / <repo>` と `<branch> <head>`、続いて `N tasks  D done  R running  Q queued`。
- `WORK` … **Relay の task tree**（`parent_task_id`）。work decomposition であり、worker の上下関係ではない。
  - 並び: 同一 parent 配下で **active が先 → priority 降順 → id 固定**（refresh でガタつかない）。
  - `done` は dim。全子孫が done の subtree は 1 行に畳む（`✓ … N done`）。
- `WORKERS` … **1 worker = 1 row**（Worker は durable、Runtime は disposable）。
  - `worker / Relay state / execution / current task / generation / pane / progress`。
  - **Relay worker state**（`starting idle working waiting_input stalled dead`）と
    **execution**（`busy idle quiet !idle starting unavailable`）は**別の列**。混ぜない。
  - generation / pane / execution は、その worker の **current runtime だけ**を表す。
  - `!idle` = 「Relay は working＋タスク保持なのに Herdr が idle、quiet リーズも無い」= unexpected idle。
  - `quiet` = Relay の bounded quiet lease（`relay wait`）中の意図的 idle。正常。
  - pane id を **Ctrl+click** するとその pane にフォーカス（要プラグイン link）。
- `ATTENTION` … derived な警告のみ（DB には書かない）。無ければ `none`。例:
  `! dp-2  T9 working but runtime idle, no quiet lease` /
  `! T14 unclaimable role=rust-perf` / `! T19 blocked_human: <reason>` /
  `! worker-3 unread messages=2 (next nudge in 42s)` /
  `! worker-x supervised worker has no visible runtime pane`。
  unread の `(next nudge in …)` は relay 本体の nudge ポリシーと同じ計算。
- `--runtime-history` … 各 worker の全 runtime 世代を表示（既定は current のみ）。
- **幅の扱い**: pane 幅に合わせて全行を 1 行に収める（全角は 2 桁）。resize に追従する。

## 判断基準

| 条件 | どうする |
| --- | --- |
| 自分（呼び出し元）の隣でよい | `relay dashboard --show` |
| 統括に相当する pane の隣に出したい | `relay dashboard --show --pane <その pane>` |
| どの pane も分割せず独立 tab にしたい | `relay dashboard --show --tab` |
| Relay がまだ無い | `relay init`（本スキルは fallback を持たない） |
| Relay を読めているか不安 | `relay dashboard --doctor` |
| 表示を変えたい | 本スキルではなく relay 本体の `src/dashboard/` を直す |
| タスクを進めたい | 本スキルではなく `relay next/note/submit`（`agent-worker` skill） |

## アンチパターン

- 表示ロジックをこのスキル側に再実装する（drift する。実体は `relay dashboard` 一本）
- DB を直接読む / 描画を独自に持つ（relay の domain 関数を必ず経由する）
- 自分の作った dashboard pane 以外を `--hide` で閉じる（relay は追跡中の pane だけを閉じる）
- 常駐させるために daemon 化する（必要なときだけ `--show` / `--hide`）
- Relay が無いのにタスク欄を推測で埋める（`relay dashboard` は**失敗する**）

## 参考

- 実装: `<relay>/src/dashboard/{command,model,render,herdr,doctor}.ts`
- relay 本体: `~/ghq/github.com/81ueman/relay`（SQLite が正本）
- Ctrl+click プラグイン: `<relay>/integrations/herdr/`
