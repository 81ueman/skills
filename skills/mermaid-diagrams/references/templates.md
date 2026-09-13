# Mermaid テンプレート一覧

コピーして使う雛形は `templates/` に置く。記法のルールは [`syntax.md`](syntax.md) を参照。
（パスはスキルのベースディレクトリ基準。）

| 雛形 | 図種 | 用途 |
| --- | --- | --- |
| `templates/flowchart.mmd` | flowchart | 処理フロー、分岐、subgraph、classDef |
| `templates/sequence.mmd` | sequenceDiagram | API/プロトコルのやり取り、alt/loop |
| `templates/class.mmd` | classDiagram | クラス、継承/集約/コンポジション |
| `templates/state.mmd` | stateDiagram-v2 | 状態遷移、ネスト状態 |
| `templates/er.mmd` | erDiagram | ER、基数、PK/FK |
| `templates/gantt.mmd` | gantt | スケジュール、マイルストーン |
| `templates/pie.mmd` | pie | 割合 |
| `templates/journey.mmd` | journey | ユーザー体験 |
| `templates/gitgraph.mmd` | gitGraph | ブランチ運用 |
| `templates/mindmap.mmd` | mindmap | マインドマップ |
| `templates/timeline.mmd` | timeline | 年表 |
| `templates/quadrant.mmd` | quadrantChart | 2 軸の位置づけ |
| `templates/requirement.mmd` | requirementDiagram | 要件と検証 |
| `templates/sankey.mmd` | sankey-beta | 流量・遷移量 |
| `templates/xychart.mmd` | xychart-beta | 棒/折れ線 |
| `templates/block.mmd` | block-beta | ブロック構成 |
| `templates/clos-network.mmd` | flowchart | ネットワーク/インフラ構成の実例 |

## 使い方

```sh
cp templates/sequence.mmd my.mmd
$EDITOR my.mmd

mmdc -i my.mmd -o my.png -b white -s 2     # 検証つきレンダリング
mmdc -i my.mmd -o my.svg
mermaid-ascii -f my.mmd -x 2 -y 1 -p 0     # ASCII
open -a Preview my.png
```

GitHub / README なら、`my.mmd` の中身をそのまま ```` ```mermaid ```` フェンスに貼る。
