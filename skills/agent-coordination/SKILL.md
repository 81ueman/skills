---
name: agent-coordination
description: Herdrで並列稼働する複数エージェント（別paneのcoordinator同士、部下スポーン含む）に作業指示・仲裁・完了検知するときに使う。scripts/coordのtask台帳＋result.json正本、binding order、バックグラウンド完了検知をまとめる。
---

# agent-coordination

Herdr上の複数エージェントpane間で、指示・仲裁・完了検知を行う手順。
正本はファイルシステム（`/tmp/coord/<task>/spec.json`＋`result.json`）。出力文字列マッチ（MARK）は使わない。

## 概要

別paneのエージェントとはユーザー経由で伝言せず、pane ID指定で直接対話する。
完了は `coord wait` の成功＋worktreeの自前検証で判定する（どちらか一方では未完了扱い）。

- 親: `coord new` → `coord prompt` → `coord wait` / `wait-all`
- 子: `coord done` で区切るか、止まらず進め続けるかの二択のみ。doneなし停止は禁止
- 各担当の成果は実行で独立検証する（報告の「tests green」は証拠とみなさない）。検証後に自担当分のみcommitする。

## いつ使うか

- 別paneのcoordinatorへ作業指示・仲裁・確認を送るとき
- 部下として新規agentをスポーンして待つとき
- 並列作業の完了をバックグラウンドで検知したいとき
- 複数担当間の順序拘束（binding order）やゲート条件を運用するとき

## 手順（coord CLI）

```bash
C=scripts/coord   # skill内の相対パス。絶対パスは ~/.agents/skills/agent-coordination/scripts/coord
T=$($C new --pane <paneID> --about 要約 -- 作業指示文)
$C prompt $T            # 完了契約付きprompt＋working遷移確認
$C wait $T --timeout 600
$C wait-all --timeout 900 $T1 $T2   # 並列は全task発行後に一括待機
$C list / $C show $T / $C retry $T
```

子への契約は次の二択のみ。半端な停止は禁止する。

- 進められる間は止まらず進め続け、区切りがついたら必ず`coord done <task> --status ok --summary 一行要約 [--commit SHA]`を実行する
- 進められない場合（質問・承認待ち・ブロッカー）は無言停止せず、必ず `coord done <task> --status fail --summary 理由と必要な入力` を実行する

完了宣言のechoやMARK文字列は不要・禁止。

状態確認は `herdr pane read <paneID> --source recent-unwrapped --lines N` と `herdr agent get <paneID>`。
`blocked`で返ったら `agent get` + `agent read` を見て承認UIか質問かを特定し、勝手に許可しない。

## パターン別手順

### P-A: 既存agentへの指示（peer / 部下prompt）

`coord new` → `coord prompt` → `coord wait` の順。`prompt` は送信結果＋working遷移の両方を確認する（`coord prompt` が `PROMPTED task=… agent_status=…` を出す。`working` にならなければpaneを確認して再送）。

`agent prompt --wait`単独はターン追跡しない（working中の別ターン終了で満たされる）。必ず `coord wait` と組にする。

子が `result.json` なしに止まったら（`wait` タイムアウト、またはagentがidle/doneなのにresultなし）、親は `coord show` + `pane read` + `agent get` で確認し、`coord retry <task>` → `coord prompt <task>` で再駆動する。放置しない。

### P-C: 新規agentをスポーン（部下・agent start）

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
herdr agent start worker-<task> --kind opencode --pane <newPaneID>
herdr agent wait <newPaneID> --timeout 120000
# 以降はP-Aと同じ（coord new → prompt → wait）
```

`agent start`はshell promptで待つ空きpaneが前提。エディタ・foregroundコマンド実行中のpaneにstartしない。
起動直後の`agent_not_ready`/`agent_prompt_stalled`は5秒以内にworkingへ遷移しない合図。`agent get`+`read`で確認し再送する。

### P-D: 複数並列の鉄則（待機置き忘れ・指示漏れ防止）

1. 全task発行→全prompt一括→`wait-all`で一括待機。1台ずつ「発行→指示→待機」を繰り返さない。
2. 台帳を作る。`coord list` で pane数 == task数を確認してから待つ。
3. promptは送信結果＋状態遷移の両方を確認する。`agent_prompted` だけでは到達保証なし。
4. pane closeは全wait完了後。待機中にcloseすると待機が死ぬ。
5. 検証NG時は `coord retry <task>` して `coord prompt` からやり直す。

### 会話パターン（親媒介）

担当を直接会話させない。親がAのresultを取り出してBへpromptする直列回しにする（`depends_on`意識）。例：提案→レビュー→最終の往復。

## 判断基準

| 条件 | どうする |
| --- | --- |
| 別paneに作業を頼みたい | `coord new --pane <paneID> -- 指示` → `coord prompt` → `coord wait` |
| 並列に複数頼みたい | 全taskを `new` してから全promptし、`coord wait-all` で一括待機 |
| やり直したい | `coord retry <task>` → `coord prompt <task>` → `coord wait <task>` |
| resultなしで止まった | `coord show`＋`pane read`＋`agent get`で確認し、`retry`→`prompt`で再駆動。doneなし停止は許容しない |
| 状態・結果を見たい | `coord show <task>`（spec＋result）、`coord list`（一覧） |
| 担当境界を跨ぐ判断 | 推測で確定しない。各担当に直接確認し、食い違いは契約文書を優先、小さなRFCに切る |
| 順序拘束が必要 | binding orderを明示し、飛ばし禁止を宣言する（例：P0-1→P0-2→P0-3）。ゲート開放条件も同時に宣言する |

## アンチパターン

- `coord done` なしに途中で止まる（無言停止・半端な区切り）。止まるなら `done --status ok|fail` で区切るか、止まらず進め続ける
- 質問・承認待ちで無言停止する（`done --status fail` に理由と必要な入力を書け）

- ユーザー経由でエージェント間の伝言をする（直接pane指定で話す）
- `coord wait` なしに `agent prompt --wait` 単独で完了宣言する（別ターンの終了で満たされる）
- `wait` / `wait-all` に `--timeout` を付けず無限待ちにする
- `agent wait` の `unknown`・一過性 `idle` を完了とみなす（必ず `coord wait` 成功＋worktree検証の両方を見る）
- バックグラウンド完了をsleep＋`pane read`反復でポーリングする（`coord wait` / `wait-all` を使う）
- 待機中にpaneをcloseする
- 他担当の未commit作業に触れる・他担当分をcommitする
- 報告の「green」を実行なしに追認する

## 参考

- Herdr操作の詳細: `herdr --skill`（未ロード時のみ）、`herdr agent wait --help`
- `scripts/coord` の使い方: `scripts/coord`（引数なしでusage表示）、`coord show <task>` でspec/result確認
