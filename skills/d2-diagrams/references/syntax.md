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
- `direction: right` をトップかコンテナ内に書くとレイアウト方向が変わる

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
g: {
  grid-rows: 2
  grid-columns: 2
  a; b
  c; d
}

n1: near n2
n2: other
```

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
d2 --layout tala --ascii-mode extended --pad 0 --stdout-format ascii in.d2 -

# 純 ASCII
d2 --layout tala --ascii-mode standard --pad 0 --stdout-format ascii in.d2 -

# ファイルへ
d2 --layout elk in.d2 out.txt
```

`--ascii-mode`: `extended`（既定、罫線あり）/ `standard`（`+ - | >` のみ）。

### ペインでライブ表示する小さなラッパ

```bash
#!/usr/bin/env bash
# live.sh <src.d2> <out.txt>
src="$1"; out="$2"; last=""
while true; do
  now=$(stat -f %m "$src" 2>/dev/null || stat -c %Y "$src")
  if [ "$now" != "$last" ]; then
    last="$now"
    d2 --layout tala --ascii-mode extended --pad 0 --stdout-format ascii "$src" - > "$out"
    printf '\033[2J\033[H'; cat "$out"
  fi
  sleep 1
done
```

## 参考リンク

- 公式: <https://d2lang.com/>
- アイコン: <https://icons.d2lang.com/>
