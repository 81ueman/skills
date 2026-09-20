# config と plan

## config: `<repo>/.agent-status/config.json`

`--config <path>` か `$AGENT_STATUS_CONFIG` で上書き可能。無ければ全項目デフォルト。

`watch`（および `show` が起動する watch）は config.json の mtime を毎ループ確認し、変更を検知すると
**次の更新で再読込**する（pane 再起動不要）。plan / relay / herdr / git は元々毎回読み直す。
`--workspace` など CLI 引数は起動時固定なので、切り替えたい場合は `show`/`watch` を再起動する。

```json
{
  "title": "Egress ACL — executable end-to-end",
  "subtitle": "HD-4 / control → lowering → Rust|Go|C++ → vendor E2E",
  "relay": { "enabled": true, "db": null },
  "plan":  { "enabled": true, "path": ".agent-status/plan.json" },
  "herdr": { "enabled": true, "workspaces": ["w50", "w61"], "cwd_match": true, "show_shells": false, "links": true },
  "kpi":   { "exclude": ["README.md", "catalog.json", "notes/", "papers/", "summaries/", ".agent-status/"] },
  "extras": [
    { "label": "fixtures", "command": ["sh", "-c", "ls -d semantic-contract/egress-* 2>/dev/null | wc -l"] },
    { "label": "commits", "command": "git rev-list --count HEAD" }
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
| `herdr.show_shells` | `false`（既定）でエージェントの居ない pane（シェル・コマンド実行）を非表示。ダッシュボード自身の pane は常に除外 |
| `herdr.links` | `true`（既定）で pane id を OSC8 リンク化。TTY のときだけ有効で、Ctrl+click でその pane へ移動（[sources.md](sources.md)） |
| `kpi.exclude` | dirty 件数から除外するパスの部分文字列 |
| `extras` | 追加 KPI。`command` の stdout を 1 行で表示。**配列は exec、文字列は shell 経由**（パイプ可）。配列を推奨。失敗時は `!(理由)` を赤字表示 |
| `watch_interval` | `watch` / `show` の更新秒数（既定 5） |

### extras の書き方

```json
"extras": [
  { "label": "fixtures", "command": ["sh", "-c", "ls -d egress-* 2>/dev/null | wc -l"] },
  { "label": "commits",  "command": "git rev-list --count HEAD" }
]
```

- 配列（推奨）: そのまま exec。シェルを介さないので安全。
- 文字列: `shell=True` で実行。パイプ・リダイレクトが使える。
- どちらも 20 秒でタイムアウト。失敗時は `?` ではなく `!(理由)`（例 `!(exit 2: ...)`, `!(not found: ...)`）を赤字で表示する。

生成物（`status-pane` など）も `.agent-status/` に置かれる。リポジトリを汚さないため
`.agent-status/` を `.gitignore` するのを推奨。

## plan: `<repo>/.agent-status/plan.json`（relay が無いときの手書き台帳）

relay が使えるときは relay のタスクが表示の主役で、plan は併記される。

```json
{
  "title": "Egress ACL program",
  "tasks": [
    { "id": "P1", "title": "Rust engine", "owner": "integrator", "status": "done" },
    { "id": "P2", "title": "Go engine mirror", "owner": "w50:p4", "status": "working", "parent": "P1" },
    { "id": "P3", "title": "C++ engine mirror", "owner": "w50:p5", "status": "delegated", "parent": "P1" },
    { "id": "P4", "title": "3-way differential", "owner": "integrator", "status": "pending",
      "note": "Go/C++ 完了後" }
  ]
}
```

- ルートを配列にしてもよい（`[{...}, {...}]`）。
- `status` は `done working delegated pending blocked` を想定（未知の値はグレー表示）。
- 表示色: `done`=緑 / `working`=黄 / `delegated`=水 / `pending`=灰 / `blocked`・`failed`=赤。
- 階層: `parent` に親タスクの `id` を書くとツリー表示（子は 2 スペース/段でインデント）。
  表記順は配列順。親が存在しない・不明な id は root（depth 0）扱い。
