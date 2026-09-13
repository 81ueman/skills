---
name: d2-diagrams
description: d2（Terrastruct D2）で図を書く/描くときに使う。インストール、svg/png/ascii へのレンダリング、watch、レイアウトエンジン（dagre/elk/tala）、テーマ、fmt/validate、および記法（node・shape・edge・label・container・style・class・vars・import・sql_table・sequence_diagram）をまとめる。ネットワーク/インフラ構成図、階層の多い図、ターミナル ASCII 表示、レイアウト制御に向く。判断スキル diagram-tool-choice から d2 が選ばれたときにロードする。
---

# D2（Terrastruct D2）

D2 は宣言的な図言語。ノードとコンテナをテキストで書き、`d2` CLI で SVG/PNG/ASCII に描画する。
インフラ/ネットワーク構成やネストの深い図に強く、レイアウトエンジンを差し替えられる。

- 使い分けの判断: `diagram-tool-choice` を参照
- **記法（文法）**: [`references/syntax.md`](references/syntax.md)
- **レイアウトエンジンの選び方**: [`references/layout-engines.md`](references/layout-engines.md)
- **コピー用の雛形と索引**: [`references/templates.md`](references/templates.md)（実体は `templates/`）

> 雛形は本文に置かない。`references/templates.md` で選び、`templates/<name>.d2` をコピーして使う。

## インストール

```sh
brew install d2          # macOS
d2 --version
brew install chafa       # 併用すると PNG をターミナル内に描画できる
```

## CLI 早見表

```sh
d2 file.d2                 # 省略時は file.svg
d2 file.d2 out.png         # svg / png / pdf / pptx / gif / txt
d2 --layout elk file.d2 out.svg
d2 -w file.d2 out.svg      # watch（保存でライブ再描画、ブラウザを開く）
d2 --browser 0 -w file.d2 out.svg   # ブラウザを開かず watch
```

| 目的 | コマンド |
| --- | --- |
| レンダリング | `d2 [flags] in.d2 out.{svg,png,pdf,pptx,gif,txt}` |
| 標準入出力 | `d2 in.d2 -`（`-` は stdin/stdout） |
| 形式を明示 | `d2 in.d2 --stdout-format png - > out.png` |
| ASCII 出力 | `d2 --stdout-format ascii --ascii-mode extended in.d2 -` |
| レイアウト | `--layout dagre\|elk\|tala` |
| テーマ | `-t <id>`（一覧 `d2 themes`） |
| 余白 | `--pad 100`（0 で詰める） |
| 手書き風 | `-s` / `--sketch` |
| 拡大縮小 | `--scale 0.5` |
| アニメ | `--animate-interval 1000`（SVG/GIF） |
| 校正 | `d2 --check in.d2` |
| 整形 | `d2 fmt in.d2 ...` |
| 構文検査 | `d2 validate in.d2`（構文のみ。shape 名の妥当性は描画で分かる） |
| レイアウト情報 | `d2 layout` / `d2 layout elk` |
| プレイグラウンド | `d2 play in.d2` |

## ワークフロー

1. [`references/templates.md`](references/templates.md) で近い雛形を選び、`templates/<name>.d2` をコピー
2. 編集する
3. **必ずレンダリングして検証**（構文・shape 名のエラーは描画時に出る）
4. 用途に応じた出力を選ぶ（画像 / ASCII）

## 最小例（動作確認用）

`templates/basic.d2` 相当:

```d2
direction: right
user: User { shape: person }
api: "API server"
db: Database { shape: cylinder }
user -> api: HTTPS
api -> db: SQL
```

## レイアウトエンジンの選び方

`dagre`/`elk` は**階層型（Sugiyama 系）**、`tala` は**階層に縛られない直交レイアウト（探索型）**で系統が違う。

| エンジン | 一言で | 使いどころ |
| --- | --- | --- |
| `dagre` | 階層に並べる軽量 Sugiyama。既定・最速 | 階層/フロー。Leaf-Spine/Clos、packet flow、依存関係 |
| `elk` | 同じ階層型を制約・ポート・配線・コンテナまで本格化 | port/link が多い、コンテナが複雑、大規模な構成図 |
| `tala` | 白板風の 2D 配置を探索。対称性・座標固定・部分固定 | WAN overview、hybrid cloud、NW+サービス+DB 混在、Visio 風 |

要点: **dagre/elk は「グラフ理論寄り」、tala は「ダイアグラムデザイン寄り」**。長く流れる DAG は dagre/elk、非階層のトポロジは tala。

- tala は `top`/`left` で座標固定、コンテナごとの `direction`、`near` を shape 指定、ができる（dagre/elk は不可）。祖先→子孫の接続は dagre では不可
- tala はランダム性があり、小変更で図が激変しうる（既定シード `1,2,3`、`tala-seeds` で変更可・同一シードで再現）。v0.9.0+ で同梱だが既定は `dagre`（opt-in）
- 指定方法は `--layout` のほか `D2_LAYOUT` 環境変数、ソース中の `vars.d2-config.layout-engine` でも可
- 詳細な比較（公式の長所短所・機能対応表・図タイプ別の早見表）: [`references/layout-engines.md`](references/layout-engines.md)

ASCII の幅・高さはエンジンと `--ascii-mode` で変わる（例: `clos.d2` を `--ascii-mode standard` で描くと `elk` 138×27 / `tala` 96×35。既定の `extended` では `elk` 268×27 / `tala` 198×35）。
ターミナルに収めたいときは `--ascii-mode`（約2倍変わる）と `--pad 0` で調整する。

## ターミナル / ASCII

```sh
# Unicode 罫線（推奨）
d2 --layout tala --ascii-mode extended --pad 0 --stdout-format ascii in.d2 -

# 純 ASCII（+ - | > のみ）
d2 --layout tala --ascii-mode standard --pad 0 --stdout-format ascii in.d2 -
```

`--ascii-mode`: `extended`（既定、罫線あり）/ `standard`（純 ASCII）。`.txt` 出力でも ASCII になる。

## 画像として確認

```sh
d2 --layout elk in.d2 out.png
open -a Preview out.png        # macOS
```

## 落とし穴

- `d2 validate` は構文しか見ない。未知の `shape` 名は**描画時に**エラーになる
- 出力パスを省略すると `.svg`。`--stdout-format` は `-` と併用する
- watch は既定でブラウザを開く。開きたくないなら `--browser 0`
- 変数は `$name` ではなく `vars: { name: ... }` + `${name}`
- `image` shape は `icon` が必須で、ホスト型アイコンは要ネットワーク
- 大きい図は `--pad`・レイアウト・`--scale` で調整（PNG は 32768px 上限）

## 参考

- 公式: <https://d2lang.com/> / アイコン: <https://icons.d2lang.com/>
- 記法: [`references/syntax.md`](references/syntax.md)
- レイアウトエンジン: [`references/layout-engines.md`](references/layout-engines.md)
- 雛形: [`references/templates.md`](references/templates.md)
