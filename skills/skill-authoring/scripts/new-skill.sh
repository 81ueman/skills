#!/usr/bin/env bash
# 新しい Agent Skill の雛形を作成し、~/.agents/skills にシンボリックリンクする。
#
# 使い方:
#   new-skill.sh <skill-name>

set -euo pipefail

usage() {
  echo "usage: $(basename "$0") <skill-name>" >&2
  exit 1
}

name="${1:-}"
[ -n "$name" ] || usage

if ! printf '%s' "$name" | grep -Eq '^[a-z][a-z0-9._-]*$'; then
  echo "error: スキル名は ^[a-z][a-z0-9._-]*$ にしてください: $name" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo="$(cd "$script_dir/../../.." && pwd -P)"
dest="$repo/skills/$name"
template="$repo/skills/skill-authoring/templates/skill-template.md"

if [ -e "$dest" ]; then
  echo "error: 既に存在します: $dest" >&2
  exit 1
fi
if [ ! -f "$template" ]; then
  echo "error: 雛形が見つかりません: $template" >&2
  exit 1
fi

mkdir -p "$dest"
sed "s/^name: .*/name: $name/" "$template" > "$dest/SKILL.md"

mkdir -p "$HOME/.agents/skills"
link="$HOME/.agents/skills/$name"
if [ -e "$link" ] || [ -L "$link" ]; then
  echo "warn: リンク先が既に存在するため作成をスキップ: $link" >&2
else
  ln -s "$dest" "$link"
fi

echo "created : $dest/SKILL.md"
echo "linked  : $link -> $dest"
echo
echo "次の手順:"
echo "  1. $dest/SKILL.md を編集"
echo "  2. $repo/README.md のスキル一覧を更新"
echo "  3. cd $repo && git add skills/$name README.md && git commit -m \"Add $name skill\" && git push"
