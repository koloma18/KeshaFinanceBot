#!/bin/bash
# Установка дизайн-скиллов для AI-агентов
# Поддерживает: Superpowers Visual Companion + Impeccable
set -e

SKILLS_DIR="$HOME/.agents/skills"
DRY_RUN=false

# --- Parse args ---
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run]"
            echo ""
            echo "Устанавливает дизайн-скиллы в ~/.agents/skills/:"
            echo "  1. Superpowers visual-companion"
            echo "  2. Impeccable (23 команды + anti-pattern detection)"
            echo ""
            echo "Options:"
            echo "  --dry-run  Показать что будет сделано, без изменений"
            exit 0
            ;;
    esac
done

echo "=== Установка Design Skills ==="
echo "Директория: $SKILLS_DIR"
echo ""

# --- 1. Superpowers — visual-companion ---
echo "📥 [1/2] Superpowers visual-companion..."
if [ "$DRY_RUN" = true ]; then
    echo "   [dry-run] mkdir -p $SKILLS_DIR/visual-companion"
    echo "   [dry-run] curl → $SKILLS_DIR/visual-companion/SKILL.md"
else
    mkdir -p "$SKILLS_DIR/visual-companion"
    curl -sL https://raw.githubusercontent.com/obra/superpowers/main/skills/brainstorming/visual-companion.md \
        -o "$SKILLS_DIR/visual-companion/SKILL.md"
    echo "   ✅ visual-companion установлен"
fi

# --- 2. Impeccable ---
echo "📥 [2/2] Impeccable (npx impeccable skills install)..."
if [ "$DRY_RUN" = true ]; then
    echo "   [dry-run] npx impeccable skills install"
else
    # Пробуем npx (современный способ)
    if command -v npx &>/dev/null; then
        npx impeccable skills install 2>/dev/null && echo "   ✅ Impeccable установлен через npx" || {
            echo "   ⚠️  npx impeccable не сработал, пробуем git clone..."
            TMP_DIR=$(mktemp -d)
            if git clone --depth 1 https://github.com/pbakaus/impeccable.git "$TMP_DIR" 2>/dev/null; then
                if [ -d "$TMP_DIR/dist/agents/.agents/skills" ]; then
                    cp -r "$TMP_DIR/dist/agents/.agents/skills/"* "$SKILLS_DIR/"
                    echo "   ✅ Impeccable skills скопированы из git"
                fi
                rm -rf "$TMP_DIR"
            else
                echo "   ❌ Не удалось установить Impeccable."
                echo "   Установи вручную: npx impeccable skills install"
                echo "   Или: git clone https://github.com/pbakaus/impeccable.git"
                echo "        cp -r impeccable/dist/agents/.agents/skills/* ~/.agents/skills/"
            fi
        }
    else
        echo "   ❌ npx не найден. Установи Node.js или скопируй вручную:"
        echo "   git clone https://github.com/pbakaus/impeccable.git /tmp/impeccable"
        echo "   cp -r /tmp/impeccable/dist/agents/.agents/skills/* ~/.agents/skills/"
    fi
fi

# --- Итог ---
echo ""
if [ "$DRY_RUN" = false ]; then
    echo "=== Установленные skills ==="
    ls -la "$SKILLS_DIR/" 2>/dev/null || echo "   (директория пуста или не существует)"
fi
echo ""
echo "💡 Использование:"
echo "   Superpowers: /visual-companion  (визуальный компаньон в браузере)"
echo "   Impeccable:  /impeccable audit|polish|critique|craft|..."
