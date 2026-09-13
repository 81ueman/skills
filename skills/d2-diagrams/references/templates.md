# d2 テンプレート一覧

コピーして使う雛形は `templates/` に置く。記法のルールは [`syntax.md`](syntax.md) を参照。
（パスはスキルのベースディレクトリ基準。）

| 雛形 | 用途 | 主な要素 |
| --- | --- | --- |
| `templates/basic.d2` | 最小構成 | `direction`, shape(person/cylinder), edge label |
| `templates/network-clos.d2` | ネットワーク/DC 構成 | cloud/hexagon/rectangle/cylinder, 色分け, 破線, Null0 |
| `templates/hierarchy.d2` | 多段の階層 | コンテナ入れ子, ラベル付きグループ, ドット短縮 |
| `templates/sequence.d2` | シーケンス | `sequence_diagram` |
| `templates/sql-table.d2` | ER/テーブル | `sql_table`, `primary_key`/`foreign_key` |
| `templates/styled-nodes.d2` | 見た目の制御 | `style`, `classes`, `vars` |

レイアウトエンジンの目安（詳細は [`layout-engines.md`](layout-engines.md)）:

| 雛形 | 第一候補 |
| --- | --- |
| `network-clos.d2` | `dagre`（大規模・コンテナ多めなら `elk`） |
| `hierarchy.d2` | `dagre` / `elk` |
| `basic.d2` / `styled-nodes.d2` | 既定の `dagre` |
| `sql-table.d2` | `elk` か `tala`（列への正確な配線） |
| `sequence.d2` | 専用レイアウトのため `--layout` の影響なし |
| 座標固定やコンテナごとの `direction` を使う | `tala` |

## 使い方

```sh
cp templates/network-clos.d2 my.d2
$EDITOR my.d2

d2 --layout elk my.d2 my.svg          # 検証つきレンダリング
d2 --layout elk my.d2 my.png
d2 --layout tala --stdout-format ascii --pad 0 my.d2 -   # ターミナル ASCII
open -a Preview my.svg
```
