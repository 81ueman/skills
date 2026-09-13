# D2 記法チートシート

`d2 v0.9.0` で検証済み。網羅より実用重視。

## コメント

```d2
# 行コメント
```

## ノードとラベル

```d2
a                          # id = ラベル
b: Label
c: "two words"
d: "line1\nline2"          # 複数行
e: |md
  ## Markdown
  - `code` も使える
|
```

- id に使えるのは英数字・`_`。ラベルに空白/記号があるなら引用
- `direction: right` で方向を変えられる。トップレベルは全エンジン共通だが、**コンテナごとの direction は tala のみ**（dagre/elk は無言で無視）

## shape

```d2
x: { shape: hexagon }
```

| 分類 | shape |
| --- | --- |
| 基本 | `rectangle`(既定) `square` `page` `parallelogram` `document` |
| データ | `cylinder` `queue` `package` `stored_data` |
| 人/判断 | `person` `diamond` `oval` `circle` |
| ネットワーク/クラウド | `hexagon` `cloud` |
| その他 | `step` `callout` `text` `code` `class` `sql_table` `sequence_diagram` |
| 画像 | `image`（`icon:` と併用。ホスト型は要ネットワーク） |

未知の shape 名は `d2 validate` では検出されず、**描画時にエラー**になる点に注意。

## エッジ

```d2
a -> b                     # 有向
a <- b
a <-> b                    # 双方向
a -- b                     # 無向
a -> b: edge label
a -> b: "複数語のラベル"
```

エッジへのスタイル:

```d2
a -> b {
  style.stroke: "#dc2626"
  style.stroke-width: 3
  style.stroke-dash: 4     # 破線
  style.animated: true
}
```

## コンテナ（グルーピング）

```d2
group: {
  a -> b
  b -> c
}

# 入れ子
outer: {
  inner: {
    x -> y
  }
}

# ドット短縮記法
a.b -> a.c
```

### タイトルとコンテナの表示名

```d2
title: "システム構成"        # 図全体のタイトル

group: My group {            # コンテナの表示名（ラベル）
  a -> b
}
```

> `title:` は ASCII 出力だと最上部のノードに重なって見えることがある。気になるときは SVG/PNG で確認する。

## スタイル

```d2
n: styled {
  style.fill: "#dbeafe"
  style.stroke: "#2563eb"
  style.stroke-width: 3
  style.stroke-dash: 4
  style.font-color: "#1e3a8a"
  style.bold: true
  style.italic: true
  style.shadow: true
  style.multiple: true     # 重ね図形
  style.3d: true
  style.opacity: 0.5
}
```

## クラス（スタイルの再利用）

```d2
classes: {
  router: { shape: hexagon; style.fill: "#fee2e2" }
}

r1: r1 { class: router }
```

## 変数

```d2
vars: {
  blue: "#dbeafe"
}

n: n { style.fill: ${blue} }
```

> `$name` 単体では使えない。`vars: {}` + `${name}` の形。

## レイアウト補助

```d2
# グリッド配置（全エンジン）
g: {
  grid-rows: 2
  grid-columns: 2
  a; b
  c; d
}
```

位置固定と `near`（**tala のみ**。dagre/elk ではコンパイルエラー）:

```d2
# 座標を固定（top と left は必ず両方セット。片方だけだとエラー）
pinned: { top: 100; left: 100 }
auto: other

# 別の図形の近くに置く（near はオブジェクト指定）
n1: { near: n2 }
n2: other
```

`near` は定数でも指定でき、こちらは全エンジン共通:

```d2
n3: { near: top-center }
```

> **`n1: near n2` は誤り。** D2 はラベルが `near n2` のノードを作るだけで、near 関係にはならない。属性として `n1: { near: n2 }` と書く。
> `near` はノード（オブジェクト）に対してのみ有効。エッジに書いても効果はない。

## tooltip / link

```d2
clickable: node {
  link: "https://example.com"
  tooltip: "説明テキスト"
}
```

## SQL テーブル

```d2
users: {
  shape: sql_table
  id: int { constraint: primary_key }
  name: varchar
  email: varchar
}
```

## シーケンス図

```d2
seq: {
  shape: sequence_diagram
  alice -> bob: request
  bob -> alice: response
}
```

## インポート

```d2
...@./shared.d2
mine: x -> base
```

## ASCII 出力とターミナル表示

```sh
# Unicode 罫線
d2 --layout tala --ascii-mode extended --stdout-format ascii in.d2 -

# 純 ASCII
d2 --layout tala --ascii-mode standard --stdout-format ascii in.d2 -

# ファイルへ
d2 --layout elk in.d2 out.txt
```

- `--ascii-mode`: `extended`（既定、罫線あり）/ `standard`（ASCII 文字のみ。`+ - | >` のほか `/ \ _ ( ) x` なども使う）
- `--ascii-mode` で変わるのは**使う文字だけ**。桁・行（表示寸法）は standard と extended で同じ
- ASCII は `--pad` も `--scale` も**効かない**（小さくしたいなら図自体を小さくする）
- `dagre` と `elk` の ASCII はバイト単位で同一になることが多い。ASCII ではエンジン差を判断できないので SVG/PNG で確認する

### ペインでライブ表示する小さなラッパ

```bash
#!/usr/bin/env bash
# live.sh <src.d2> <out.txt>
src="$1"; out="$2"; last=""
while true; do
  now=$(stat -f %m "$src" 2>/dev/null || stat -c %Y "$src")
  if [ "$now" != "$last" ]; then
    last="$now"
    d2 --layout tala --ascii-mode extended --stdout-format ascii "$src" - > "$out"
    printf '\033[2J\033[H'; cat "$out"
  fi
  sleep 1
done
```

## 参考リンク

- 公式: <https://d2lang.com/>
- アイコン: <https://icons.d2lang.com/>
