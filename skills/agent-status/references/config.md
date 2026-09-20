# config と plan

## config: `<repo>/.agent-status/config.json`

`--config <path>` か `$AGENT_STATUS_CONFIG` で上書き可能。無ければ全項目デフォルト。

```json
{
  "title": "Egress ACL — executable end-to-end",
  "subtitle": "HD-4 / control → lowering → Rust|Go|C++ → vendor E2E",
  "relay": { "enabled": true, "db": null },
  "plan":  { "enabled": true, "path": ".agent-status/plan.json" },
  "herdr": { "enabled": true, "workspaces": ["w50", "w61"], "cwd_match": true },
  "kpi":   { "exclude": ["README.md", "catalog.json", "notes/", "papers/", "summaries/", ".agent-status/"] },
  "extras": [
    { "label": "egress fixtures", "command": "ls -d semantic-contract/egress-* | wc -l" }
  ],
  "watch_interval": 5
}
```

| キー | 意味 |
| --- | --- |
| `title` / `subtitle` | 見出し。未指定なら repo ディレクトリ名 |
| `relay.db` | 明示したい relay DB パス（通常は自動探索でよい） |
| `herdr.workspaces` | 跨いで見る Herdr workspace（`--workspace` で上書き追加） |
| `herdr.cwd_match` | `<repo>` 配下の cwd の pane だけに絞る |
| `kpi.exclude` | dirty 件数から除外するパスの部分文字列 |
| `extras` | 追加 KPI。`command` の stdout を 1 行で表示 |
| `watch_interval` | `watch` / `show` の更新秒数（既定 5） |

生成物（`status-pane` など）も `.agent-status/` に置かれる。リポジトリを汚さないため
`.agent-status/` を `.gitignore` するのを推奨。

## plan: `<repo>/.agent-status/plan.json`（relay が無いときの手書き台帳）

relay が使えるときは relay のタスクが表示の主役で、plan は併記される。

```json
{
  "title": "Egress ACL program",
  "tasks": [
    { "id": "P1", "title": "Rust engine", "owner": "integrator", "status": "done" },
    { "id": "P2", "title": "Go engine mirror", "owner": "w50:p4", "status": "working" },
    { "id": "P3", "title": "C++ engine mirror", "owner": "w50:p5", "status": "delegated" },
    { "id": "P4", "title": "3-way differential", "owner": "integrator", "status": "pending",
      "note": "Go/C++ 完了後" }
  ]
}
```

- ルートを配列にしてもよい（`[{...}, {...}]`）。
- `status` は `done working delegated pending blocked` を想定（未知の値はグレー表示）。
- 表示色: `done`=緑 / `working`=黄 / `delegated`=水 / `pending`=灰 / `blocked`・`failed`=赤。
