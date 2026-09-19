---
name: agent-coordination
description: Herdrで並列稼働する複数エージェント（別paneのcoordinator同士）に作業指示・仲裁・完了検知するときに使う。pane指定の直接対話、binding order、バックグラウンド完了検知をまとめる。
---

# agent-coordination

Herdr上の複数エージェントpane間で、指示・仲裁・完了検知を行う手順。

## 概要

別paneのエージェントとはユーザー経由で伝言せず、pane ID指定で直接対話する。完了検知はpane文字列マッチよりworktree状態を見る方式を優先する（文字列マッチは自文復唱に誤発火する）。

## いつ使うか

- 別paneのcoordinatorへ作業指示・仲裁・確認を送るとき
- 並列作業の完了をバックグラウンドで検知したいとき
- 複数担当間の順序拘束（binding order）やゲート条件を運用するとき

## 手順

1. paneを確認する（`herdr pane list`）。担当paneのID・状態・cwdを特定する。
2. 指示は `herdr agent prompt <paneID> "..."` で直接送る。同一行に収める（末尾改行はzshを壊す）。応答待ちが必要な場合のみ `--wait` を同行に付ける。
3. 状態確認は `herdr pane read <paneID> --source recent-unwrapped --lines N`。`recent-unwrapped` で折り返しなしの素直なテキストが取れる。
4. 完了検知はバックグラウンドshellで待ち、完了通知を受け取る。ポーリング（sleep連打・出力ファイルの反復読み）しない。
5. 各担当の成果は実行で独立検証する（commit messageの「tests green」は証拠とみなさない）。検証後に自担当分のみcommitする。

## 判断基準

| 条件 | どうする |
| --- | --- |
| 真の完了条件がworktree/テスト結果で判定できる | `readiness.py --watch` 型のfingerprint監視を使う。変化時のみ全検査し、条件成立でexit 0（例：`--milestone conditions --watch --interval 60`） |
| pane出力の特定文字列で完了を知りたい | `herdr pane wait-output --source recent-unwrapped --lines N --timeout <MS> --match <TEXT> <paneID>` をbackground実行する。`--timeout` 必須 |
| 指示文自体がマーカー文字列を含む | そのマーカーへの待機は即時誤発火する。待機開始→指示の順にし、指示文にはマーカーを断片記述のみにする（例：「第1片 P03、第2片 DONE、ハイフン連結」）。それでも復唱リスクがあるためworktree方式を優先する |
| エージェントの生死・状態遷移を待ちたい | `herdr agent wait <paneID> --until idle|done|blocked --timeout <MS>`。`--until`省略時はidle/done/blockedにマッチ |
| 検証マイルストーンの着地（commit記録運用）を見逃したくない | `scripts/head-watch.sh <repo> [interval] [timeout]` をbackground実行する。HEAD移動時のみ発火し、新commit一覧を出す。pane文字列マッチより誤発火が少ない |
| 担当境界を跨ぐ判断 | 推測で確定しない。各担当に直接確認し、食い違いは契約文書を優先、小さなRFCに切る |
| 順序拘束が必要 | binding orderを明示し、飛ばし禁止を宣言する（例：P0-1→P0-2→P0-3）。ゲート開放条件も同時に宣言する |

## アンチパターン

- ユーザー経由でエージェント間の伝言をする（直接pane指定で話す）
- 待機対象のマーカー文字列を指示文にそのまま書く（自文復唱に即時マッチする）
- `wait-output` に `--timeout` を付けず無限待ちにする
- バックグラウンド完了をsleep＋出力読みでポーリングする
- 他担当の未commit作業に触れる・他担当分をcommitする
- 報告の「green」を実行なしに追認する

## 参考

- Herdr操作の詳細: `herdr --skill`（未ロード時のみ）、`herdr agent wait --help`、`herdr pane wait-output --help`
- 実例: `nv-papers` の `integration-contract/readiness.py --milestone conditions --watch`（fingerprint変化時のみ全検査）
