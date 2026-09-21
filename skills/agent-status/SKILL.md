---
name: agent-status
description: Relay control plane の read-only ダッシュボードを、呼び出し中の pane の隣に表示する。Relay (SQLite) の task tree / worker / runtime を正本とし、Herdr の実行状態（busy/idle）を重ね、git を補助 KPI として ANSI で自動更新する。「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスク一覧」「タスクの進み具合」「agent-status」などで使う。
slash: true
---

# agent-status

## 概要

**Relay を正本とする read-only ダッシュボード**。複数エージェント（Relay worker / Herdr pane）に
またがる作業を 1 画面に集約する。常駐はせず、明示的に呼び出したときだけ Herdr ペインを 1 枚開いて自動更新する。

```
agent-status = Relay control plane の read-only projection
             + Herdr の live execution overlay
             + git の軽い補助情報
```

原則:

```
Relay is the source of truth.
Workers are peers.
Tasks may form a parent/child work-decomposition tree (not an agent hierarchy).
Herdr is execution telemetry, not work state.
agent-status only observes and renders.
```

**Relay は必須**。`.relay/state.db` が無ければ明確に失敗する（`relay init` を促す）。計画台帳の
fallback は持たない — 仕事の構造は Relay の task tree だけで表現する。本スキルは表示専用で、
タスクの追加・claim・submit・wake・message 送信などは一切行わない（それは `relay` CLI の仕事）。
DB は **`mode=ro`（read-only）** でしか開かない。

## いつ使うか

- 複数 worker にまたがる作業の残タスク/完了/attention を俯瞰したいとき
- 単独作業でも、自分の pane の隣に進捗を出しておきたいとき
- 「進捗を見せて」「状況は」「ダッシュボード出して」「残りタスクは」と言われたとき
- 手動起動: `/agent-status`

## 前提

- Herdr 内で実行していること（`HERDR_ENV=1`）。ペイン表示は Herdr 必須。
- Relay の control plane が存在すること: `<repo>/.relay/state.db`（`relay init`）。
- pane id の **Ctrl+click 移動**を使うには Herdr プラグインを一度 link しておく（任意）:

  ```bash
  herdr plugin link ~/.agents/skills/agent-status/herdr-plugin   # プラグイン id: agent-status.pane-links
  ```

## 手順

入口は `scripts/status`（Python3 stdlib のみ）。

1. 検出状態を確認する（Relay / Herdr が使えるか）:

   ```bash
   python3 scripts/status doctor --repo "$PWD"
   ```

2. 呼び出し元 pane の隣にライブ表示を出す:

   ```bash
   python3 scripts/status show --repo "$PWD"
   python3 scripts/status show --pane w52:p2M --direction right --repo "$PWD"
   python3 scripts/status show --tab --repo "$PWD"        # 独立 tab（他 pane を分割しない）
   ```

   - 既存の status pane があれば**再利用**する（移すときは `hide` → `show`）。
   - 対象 workspace を明示する場合は `--workspace w50 --workspace w61`（複数可）。

3. 止める / 一回だけ見る / 機械可読:

   ```bash
   python3 scripts/status hide --repo "$PWD"
   python3 scripts/status render --repo "$PWD"
   python3 scripts/status render --json --repo "$PWD"
   python3 scripts/status watch --repo "$PWD" --interval 5
   ```

## 表示の読み方

- ヘッダ: `relay / <repo>` と `<branch> <head>`、続いて `N tasks  D done  R running  Q queued …` の要約。
- `WORK` … **Relay の task tree**（`parent_task_id`）。work decomposition であり、worker の上下関係ではない。
  - 並び: 同一 parent 配下で **active が先 → priority 降順 → id 固定**（refresh でガタつかない）。
  - `done` は dim。`running` は緑、`review` は黄、`blocked_*` / `failed` は目立つ色。
  - 全子孫が done の subtree は 1 行に畳む（`✓ T12 … (5/5 done)`）。同階層の done が続く場合も
    `✓ … +94 done` のように畳む（active branch を優先）。
  - 行は `state / id / title / role / [assignee]`。狭い pane では role→owner の順に落とす。
- `WORKERS` … **Relay worker が主体**。`worker / Relay state / Herdr 実行状態 / current task / progress`。
  - **Relay worker state**（`starting idle working waiting_input stalled dead`）と
    **Herdr 実行状態**（`busy idle !idle unavailable`、`quiet <残り>`）は**別の列**。混ぜない。
  - `!idle` は「Relay は working＋タスク保持なのに Herdr が idle、quiet リーズも無い」= unexpected idle。
  - `quiet <残り>` は Relay の bounded quiet lease（`relay wait`）中の意図的 idle。正常表示。
- `ATTENTION` … derived な警告のみ（DB には書かない）。無ければ `none`。例:
  `! dp-2  T9 working but runtime idle, no quiet lease  2m14s` /
  `! T14 unclaimable role=rust-perf` / `! reviewer-2 dead generation=4` /
  `! T19 blocked_human: <reason>` / `! worker-3 unread messages=2` /
  `! worker-x supervised worker has no visible runtime pane`。
- `RUNTIMES` … worker 主体の一覧: `worker / g<世代> / pane / Herdr agent_status`。
  pane id を **Ctrl+click** するとその pane にフォーカス（要プラグイン link、`herdr.links=false` で無効）。
  戻るときは Herdr の `keys.last_pane`（例 `prefix+semicolon`）。
- `sources` … `relay:<name>` と `herdr:on|off`。
- **幅の扱い**: pane 幅に合わせて全行を 1 行に収める（**全角は 2 桁**）。狭いときは role→priority→
  progress→generation→workspace の順に落とし、`RUNTIMES` 自体を省略する。resize に追従する。

## 判断基準

| 条件 | どうする |
| --- | --- |
| 自分（呼び出し元）の隣でよい | `status show` |
| 統括に相当する pane の隣に出したい | `status show --pane <その pane>` |
| どの pane も分割せず独立 tab にしたい | `status show --tab` |
| 複数 workspace を跨ぐ | `status show --workspace w50 --workspace w61` |
| Relay がまだ無い | `relay init`（本スキルは fallback を持たない） |
| 表示を変えたい（KPI 追加・除外） | `.agent-status/config.json` を編集 |
| Relay を読めているか不安 | `status doctor`（relay db / tasks / workers / runtimes / runtime links / daemon socket） |
| タスクを進めたい | 本スキルではなく `relay next/note/submit`（`agent-worker` skill） |

## アンチパターン

- `HERDR_ENV != 1` で `status show` を呼ぶ（ペインを作れない。`render` を使う）
- Relay DB を書き込みモードで開く / 本スキルから `relay` コマンドを実行する（表示専用・read-only）
- Relay が無いのにタスク欄を推測で埋める（本スキルは**失敗する**）
- 自分の作った status pane 以外を `hide` で閉じる（追跡中の pane だけを閉じる）
- 常駐させるために daemon 化する（必要なときだけ `show`/`hide`）

## 参考

- データソース: [references/sources.md](references/sources.md)
- config スキーマ: [references/config.md](references/config.md)
- 設定雛形: [templates/config.json](templates/config.json)
- Ctrl+click プラグイン: [herdr-plugin/](herdr-plugin/)
- relay 本体: `~/ghq/github.com/81ueman/relay`（SQLite が正本）
