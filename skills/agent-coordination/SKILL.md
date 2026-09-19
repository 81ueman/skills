---
name: agent-coordination
description: Herdrで並列稼働する複数エージェント（別paneのcoordinator同士、部下スポーン含む）に作業指示・仲裁・完了検知するときに使う。UUIDマーカー+sentinel file+agent waitの3点一致、binding order、バックグラウンド完了検知をまとめる。
---

# agent-coordination

Herdr上の複数エージェントpane間で、指示・仲裁・完了検知を行う手順。
部下パターン（plain paneでのコマンド実行、新規agentスポーン、既存agentへのprompt）すべてで同じ完了定義を使う。

## 概要

別paneのエージェントとはユーザー経由で伝言せず、pane ID指定で直接対話する。
完了は単一シグナルのみで判定しない。次の3点一致を必須にする（1つでも欠けたら未完了扱い）：

1. sentinel file（UUID付きDONEファイル）が非空で存在する
2. `herdr agent wait` または `herdr pane wait-output` がUUIDマーカーにマッチする
3. worktreeを自前で検証する（tests実行、`git status`/`git log`確認）

文字列マッチ単独は自文復唱に誤発火する。`DONE`・`完了`・`green`など汎用語をマーカーにしない。

## いつ使うか

- 別paneのcoordinatorへ作業指示・仲裁・確認を送るとき
- 部下としてplain paneにコマンドを投げる／新規agentをスポーンして待つとき
- 並列作業の完了をバックグラウンドで検知したいとき
- 複数担当間の順序拘束（binding order）やゲート条件を運用するとき

## 手順（共通：UUID + sentinel）

1. paneを確認する（`herdr pane list`）。担当paneのID・状態・cwdを特定する。
2. UUIDを切る。`TASK=$(uuidgen | cut -c1-8 | tr a-z A-Z)`、`TASKL=$(echo $TASK | tr A-Z a-z)`、`MARK="DONE-$TASK"`、`SFILE="/tmp/done-$TASKL.md"`。`MARK`は他と衝突しない。
3. 待機を先にbackgroundで起動し、次に指示を送る。この順序で短時間タスクの取りこぼしを防ぐ。
4. 指示文・`pane run`文に `MARK` の連結形（例：`DONE-AB12CD34`）を直書きしない。直書きは送信行自体に即時マッチする（実測：UUIDでも0.005秒で誤発火）。`M1=DONE`・`M2=$TASK`・`S=$SFILE` の断片で渡し、子に `echo $M1-$M2` で組み立てさせる。子への契約は「完了したら `echo $M1-$M2` し、`$S` に `STATUS / SUMMARY / COMMIT` を書け。pane出力だけ・ファイルだけでは完了とみなさない」。
5. 親は両方の待機が終わってから `agent get` + `pane read` + `SFILE`内容 + worktree検証の4点を見て完了宣言する。
6. 誤発火後の再待機は必ず新MARKで張り直す。`wait-output`はワンショットで、同一MARKで再待機するとscrollbackに即時マッチして二重誤発火する。検証NG時は`TASK`を切り直し、手順3からやり直す（掛け忘れ防止）。`sentinel-wait.sh`の再実行は同`SFILE`で可だが、完了宣言には新MARK側の`wait-output`成功も必須にする。
7. 各担当の成果は実行で独立検証する（commit messageの「tests green」は証拠とみなさない）。検証後に自担当分のみcommitする。

指示は `herdr agent prompt <paneID> "..."` で直接送る。同一行に収める（末尾改行はzshを壊す）。
状態確認は `herdr pane read <paneID> --source recent-unwrapped --lines N`。

## パターン別手順

### P-A: 既存agentへの指示（peer / 部下prompt）

```bash
TASK=$(uuidgen | cut -c1-8 | tr a-z A-Z); TASKL=$(echo $TASK | tr A-Z a-z); MARK="DONE-$TASK"; SFILE="/tmp/done-$TASKL.md"
herdr pane wait-output --source recent-unwrapped --lines 50 --timeout 3600000 --match "$MARK" <paneID> &
herdr agent wait <paneID> --timeout 3600000 &
# MARK連結形をpromptに直書きしない。M1/M2/Sの断片で渡す
herdr agent prompt <paneID> "作業内容…。M1=DONE、M2=$TASK、S=$SFILE。完了したら echo \$M1-\$M2 し、\$S に STATUS/SUMMARY/COMMIT を書け" --timeout 3600000
scripts/sentinel-wait.sh "$SFILE" 3600
```

`agent prompt --wait`単独はターン追跡しない（working中の別ターン終了で満たされる）。必ずsentinelと組み合わせる。
`blocked`で返ったら `agent get` + `agent read` を見て承認UIか質問かを特定し、勝手に許可しない。

### P-B: plain paneでコマンド実行（部下・コマンド）

```bash
TASK=$(uuidgen | cut -c1-8 | tr a-z A-Z); TASKL=$(echo $TASK | tr A-Z a-z); MARK="DONE-$TASK"; SFILE="/tmp/done-$TASKL.md"
herdr pane wait-output --source recent-unwrapped --lines 50 --timeout 600000 --match "$MARK" <paneID> &
# MARK直書きNG。M1/M2変数で組み立てる（送信行への即時マッチを防ぐ。直書きは実測0.005秒で誤発火、断片化は3秒sleep後に正しく発火）
herdr pane run <paneID> "M1=DONE; M2=$TASK; S=$SFILE; (do-work; echo STATUS… > \$S) && echo \$M1-\$M2 || echo FAIL-\$M1-\$M2"
scripts/sentinel-wait.sh "$SFILE" 600
```

`pane run`はコマンド文字列自体がpaneに残る。UUIDだけでは不十分で、断片化が必須（前版の主因）。

### P-C: 新規agentをスポーン（部下・agent start）

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
herdr agent start worker-<task> --kind opencode --pane <newPaneID>
herdr agent wait <newPaneID> --timeout 120000
# 以降はP-Aと同じ（waiter-first → prompt → sentinel-wait）
```

`agent start`はshell promptで待つ空きpaneが前提。エディタ・ foregroundコマンド実行中のpaneにstartしない。
起動直後の`agent_not_ready`/`agent_prompt_stalled`は5秒以内にworkingへ遷移しない合図。`agent get`+`read`で確認し再送する。

### P-D: 複数並列の鉄則（待機置き忘れ・指示漏れ防止）

1. 全waiter先行→全prompt一括。1台ずつ「待機→指示」を繰り返さない。Bのwaiterを張る前にAへ指示すると順序が崩れる。
2. 台帳を作る。pane数 == waiter数 == prompt数 == sentinel数を送信前に数える。
3. promptは送信結果＋状態遷移の両方を確認する。`agent_prompted` だけでは到達保証なし。`agent get` でworking確認まで行う。
4. pane closeは全waiter完了後。待機中にcloseすると `pane_not_found` で待機が死ぬ（実測）。
5. `wait-output`単独に頼らない。取りこぼし時はsentinel＋idle＋成果物で3点確認する。

## 判断基準

| 条件 | どうする |
| --- | --- |
| 真の完了条件がworktree/テスト結果で判定できる | `readiness.py --watch` 型のfingerprint監視を使う。変化時のみ全検査し、条件成立でexit 0（例：`--milestone conditions --watch --interval 60`） |
| pane出力の特定文字列で完了を知りたい | UUID付き `MARK="DONE-$(uuidgen短縮)"` を作り、`herdr pane wait-output --source recent-unwrapped --lines N --timeout <MS> --match <MARK> <paneID>` をbackground実行する。`--timeout` 必須。待機開始→指示の順にし、指示/`pane run`文に`MARK`連結形を直書きせずM1/M2断片で渡す（直書きは実測0.005秒で誤発火） |
| sentinel fileで確実に知りたい | `scripts/sentinel-wait.sh <SFILE> [timeout_sec]` をbackground実行する。UUID付きパスで空ファイル誤検知を避ける（P-A/P-B参照） |
| エージェントの生死・状態遷移を待ちたい | `herdr agent wait <paneID> --timeout <MS>`（`--until`省略時はidle/done/blocked）。`--timeout` 必須。単独で完了宣言せずsentinelと組にする。`unknown`は完了とみなさない |
| 検証マイルストーンの着地（commit記録運用）を見逃したくない | `scripts/head-watch.sh <repo> [interval_sec] [timeout_sec]` をbackground実行する。HEAD移動時のみ発火する。commitしない完了は拾えないためsentinelと併用する |
| 担当境界を跨ぐ判断 | 推測で確定しない。各担当に直接確認し、食い違いは契約文書を優先、小さなRFCに切る |
| 順序拘束が必要 | binding orderを明示し、飛ばし禁止を宣言する（例：P0-1→P0-2→P0-3）。ゲート開放条件も同時に宣言する |

## アンチパターン

- ユーザー経由でエージェント間の伝言をする（直接pane指定で話す）
- `DONE`・`完了`・`green`など汎用語をマーカーにする（自文復唱・既存出力に即時マッチする。UUID必須）
- `MARK`連結形を指示文・`pane run`文に直書きする（送信行に即時マッチする。実測0.005秒で誤発火。M1/M2断片必須）
- 指示より後に待機を開始する（短時間タスクを取りこぼす）
- `wait-output` / `agent wait` に `--timeout` を付けず無限待ちにする
- `agent prompt --wait` 単独で完了宣言する（ターン追跡しないため別ターンの終了で満たされる）
- `agent wait` の `unknown`・一過性 `idle` を完了とみなす（必ずsentinel+検証と3点一致させる）
- 誤発火後に同一MARKで再待機する・再待機を掛け忘れる（ワンショット消費のため新TASKで張り直す）
- バックグラウンド完了をsleep＋`pane read`反復でポーリングする（`wait-output`/`sentinel-wait.sh`/`head-watch.sh`を使う）
- 他担当の未commit作業に触れる・他担当分をcommitする
- 報告の「green」を実行なしに追認する

## 参考

- Herdr操作の詳細: `herdr --skill`（未ロード時のみ）、`herdr agent wait --help`、`herdr pane wait-output --help`
- 実例: `nv-papers` の `integration-contract/readiness.py --milestone conditions --watch`（fingerprint変化時のみ全検査）

## coord CLI（v0・MARK不要）

生の`wait-output`/`agent wait`運用は台帳忘れ・pane close競合が起きるため、`scripts/coord`に集約する。
正本は`/tmp/coord/<task>/spec.json`＋`result.json`。出力文字列マッチ（MARK）は使わない。

```bash
C=scripts/coord
T=$($C new --pane <paneID> --about 要約 -- 作業指示文)
$C prompt $T            # 断片契約付きprompt＋working遷移確認
$C wait $T --timeout 600
$C wait-all --timeout 900 $T1 $T2   # 並列は全task発行後に一括待機
$C list / $C show $T / $C retry $T
```

子への契約は「終了時に`coord done <task> --status ok --summary …`を実行」のみ。
会話パターンは親媒介（A result→B prompt）を`depends_on`意識で直列に回す。
実測：opencode 2並列＋提案→レビュー→最終の3往復すべてok。
