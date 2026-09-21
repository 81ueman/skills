# config スキーマ

`<repo>/.agent-status/config.json`（任意）。表示中に編集すると次の更新で反映される。
指定は `--config <path>` か `$AGENT_STATUS_CONFIG` でも可能。

```json
{
  "title": null,
  "subtitle": null,
  "relay": { "db": null },
  "herdr": {
    "enabled": true,
    "workspaces": [],
    "cwd_match": true,
    "links": true
  },
  "kpi": { "exclude": ["README.md", "catalog.json", "notes/", "papers/", "summaries/", ".agent-status/"] },
  "extras": [],
  "watch_interval": 5
}
```

| キー | 既定 | 意味 |
| --- | --- | --- |
| `title` | `null` | ヘッダ左の見出し（既定は `<repo>` 名） |
| `subtitle` | `null` | 見出し下の 1 行説明 |
| `relay.db` | `null` | Relay DB の上書きパス（既定は cwd から上方探索した `.relay/state.db`）。**Relay は必須**。無ければエラー |
| `herdr.enabled` | `true` | Herdr 実行状態を重ねるか（`HERDR_ENV=1` のときだけ有効） |
| `herdr.workspaces` | `[]` | 読む workspace。**relay が worker を置いている workspace は自動で足される**ので、pane を移しても設定漏れで欠けない。`--workspace` を渡すとその範囲だけ |
| `herdr.cwd_match` | `true` | `<repo>` 配下の cwd の pane だけに絞る |
| `herdr.links` | `true` | pane id を OSC8 リンク化（TTY のときだけ）。Ctrl+click でその pane へ |
| `kpi.exclude` | 上記 | dirty 件数から除外するパスの部分文字列 |
| `extras` | `[]` | 追加 KPI。`command` の stdout を 1 行で表示。**配列は exec、文字列は shell 経由**（パイプ可）。配列推奨。失敗時は `!(理由)` を赤字表示 |
| `watch_interval` | `5` | `watch` / `show` の更新秒数 |

## 削除されたキー（旧バージョン）

`plan.*`（`enabled` / `path` / `stall_after_minutes`）、`relay.enabled` は**廃止**。
Relay が必須になったため `relay.db` の上書きだけを見る。`plan.json` の fallback は無い。
