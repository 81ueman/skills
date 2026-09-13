# Mermaid 記法チートシート

`@mermaid-js/mermaid-cli 11.17.0` で描画確認済み。

## 共通

````markdown
```mermaid
---
title: 図のタイトル
---
%%{init: {"theme":"neutral","themeVariables":{"fontSize":"16px"}}}%%
flowchart LR
  A --> B
```
````

- 1 ファイル 1 図が基本（`mmdc -i doc.md` なら複数可）
- コメントは `%%`（`%%{init: ...}%%` と混同しないよう行頭で使う）

## flowchart / graph

```mermaid
flowchart LR
  A[Start] --> B{OK?}
  B -->|yes| C[(DB)]
  B -->|no| D([End])
  subgraph G[Group]
    direction TB
    C --> D
  end
  classDef hi fill:#dbeafe,stroke:#2563eb
  class A hi
  style B fill:#fee2e2
  linkStyle 0 stroke:#f00,stroke-width:2px
  click A "https://example.com" "tooltip"
```

- 方向: `LR` `RL` `TB` `TD` `BT`
- 形状:

  | 記法 | 形 |
  | --- | --- |
  | `A[text]` | 四角 |
  | `A(text)` | 角丸 |
  | `A([text])` | スタジアム/丸 |
  | `A[[text]]` | サブルーチン |
  | `A[(text)]` | データベース（円柱） |
  | `A((text))` | 円 |
  | `A{text}` | ひし形 |
  | `A{{text}}` | 六角形 |
  | `A[/text/]` | 平行四辺形 |
  | `A[\text\]` | 逆平行四辺形 |
  | `A>text]` | 旗 |

- エッジ: `-->` `---` `-.->` `==>` `--o` `--x` `<-->`、ラベル `-->|t|` / `-- t -->`
- 複数行: `A["line1<br/>line2"]`

## sequenceDiagram

```mermaid
sequenceDiagram
  autonumber
  participant A as Alice
  actor B as Bob
  A->>B: request
  activate B
  B-->>A: response
  deactivate B
  loop retry
    A->>B: ping
  end
  alt ok
    B-->>A: 200
  else fail
    B-->>A: 500
  end
  par
    A->>B: one
  and
    A->>B: two
  end
  Note over A,B: note text
```

- 矢印: `->>`（実線矢印）`-->>`（破線）`->`（線）`-x` `-)` `<<->>` `<<-->>`
- ブロック: `loop` `alt/else` `opt` `par/and` `critical` `rect`、`activate/deactivate`、`Note`

## classDiagram

```mermaid
classDiagram
  direction LR
  class Animal {
    +String name
    -int age
    +makeSound() void
  }
  class Dog
  Animal <|-- Dog
  Animal *-- Leg
  Animal o-- Owner
  Animal --> Owner : has
```

- 関係: `<|--`（継承）`*--`（コンポジション）`o--`（集約）`-->`（関連）`..>`（依存）`..|>`（実現）

## stateDiagram-v2

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Running: start
  Running --> Idle: stop
  state Running {
    [*] --> Fast
    Fast --> Slow
  }
  Running --> [*]
```

## erDiagram

```mermaid
erDiagram
  CUSTOMER ||--o{ ORDER : places
  ORDER ||--|{ LINE_ITEM : contains
  CUSTOMER {
    string id PK
    string name
    string email FK
  }
```

- 基数: `||--||`（1対1）`||--o{`（1対多）`}o--||` `}o--o{`（多対多）
- 属性のキー: `PK` `FK` `UK`

## gantt

```mermaid
gantt
  title Project
  dateFormat YYYY-MM-DD
  axisFormat %m/%d
  section Design
    Task A :a1, 2024-01-01, 5d
  section Build
    Task B :after a1, 10d
    Milestone :milestone, 2024-02-01, 0d
```

## pie

```mermaid
pie title Share
  "A" : 45
  "B" : 30
  "C" : 25
```

## journey

```mermaid
journey
  title My day
  section Morning
    Wake: 5: Me
    Coffee: 3: Me, You
```

## gitGraph

```mermaid
gitGraph
  commit
  branch dev
  commit
  checkout main
  merge dev
```

## mindmap

```mermaid
mindmap
  root((root))
    A
      A1
      A2
    B
```

## timeline

```mermaid
timeline
  title History
  2020 : A
  2021 : B : C
```

## quadrantChart

```mermaid
quadrantChart
  x-axis Low --> High
  y-axis Low --> High
  quadrant-1 Q1
  quadrant-2 Q2
  quadrant-3 Q3
  quadrant-4 Q4
  Point A: [0.3, 0.6]
  Point B: [0.8, 0.2]
```

## requirementDiagram

```mermaid
requirementDiagram
  requirement req1 {
    id: 1
    text: must work
    risk: medium
    verifymethod: test
  }
  element e1 {
    type: sim
  }
  e1 - satisfies -> req1
```

## sankey-beta

```mermaid
sankey-beta
A,B,10
B,C,5
```

## xychart-beta

```mermaid
xychart-beta
  title "Sales"
  x-axis [a, b, c]
  y-axis 0 --> 100
  bar [10, 50, 80]
  line [10, 50, 80]
```

## block-beta

```mermaid
block-beta
  columns 3
  a b c
  d:3
```

## CLI 補足

```sh
# Markdown 内の ```mermaid を一括レンダリング
mmdc -i doc.md -o out.md -a ./assets      # 画像を書き戻し

# 設定ファイル（mermaid の initialize 相当）
mmdc -i in.mmd -o out.png -c mermaid-config.json

# puppeteer 設定（コンテナで --no-sandbox）
mmdc -i in.mmd -o out.png -p puppeteer-config.json
```

```jsonc
// puppeteer-config.json
{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }
```

## mermaid-ascii の制約

- 対応: flowchart / graph、sequenceDiagram など（図種により精度が違う）
- 無視される: subgraph、classDef/style/linkStyle、一部の shape（六角形・円柱などは四角に近似）
- 余白: `-x`（水平）`-y`（垂直）`-p`（ボックス内）で詰める
- 例: `mermaid-ascii -f in.mmd -x 2 -y 1 -p 0`
