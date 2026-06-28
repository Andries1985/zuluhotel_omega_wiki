#!/usr/bin/env bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Synchronizer - Single Page Deployment Variant
# ==============================================================================
# Usage:
#    ./update_single_page.sh <npctemplate_id>
# ==============================================================================

set -e

OUTPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/output"
HOST_STAGE_DIR="$HOME/wiki_import_single"
CONTAINER_NAME="zuluhotelomega-wiki"
CONTAINER_TARGET_DIR="/var/www/html/maintenance/wiki_import_single"

TARGET_ARG="${1:-alligator}"
CLEAN_ARG=$(echo "$TARGET_ARG" | tr '[:upper:]' '[:lower:]' | tr -d ' _')

FILE_PATH=""
for file in "$OUTPUT_DIR"/*.txt; do
    [ -e "$file" ] || continue
    base_name=$(basename "$file" .txt)
    
    # Skip matching category structural files themselves directly
    if [[ "$base_name" == Category_* ]]; then continue; fi

    clean_file=$(echo "$base_name" | tr '[:upper:]' '[:lower:]' | tr -d ' _')

    if [ "$clean_file" = "$CLEAN_ARG" ]; then
        FILE_PATH="$file"
        break
    fi
done

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    echo "❌ Error: Expected parsed text payload file for '$TARGET_ARG' is missing in output directory."
    echo "💡 Please ensure you execute the configuration compiler first:"
    echo "    python3 test_parse_npc.py $TARGET_ARG"
    exit 1
fi

TARGET_NPC=$(basename "$FILE_PATH" .txt)
echo "🚀 Isolated Sync initiated for script template reference: [$TARGET_ARG] -> ($TARGET_NPC)"

echo "📦 Preparing localized staging directory..."
rm -rf "$HOST_STAGE_DIR"
mkdir -p "$HOST_STAGE_DIR"
mkdir -p "$HOST_STAGE_DIR/Category"

# Copy the primary NPC profile page
cp "$FILE_PATH" "$HOST_STAGE_DIR/"

# Parse out the category string declared inside the file to dynamically capture its structural dependency
CATEGORY_EXTRACTED=$(grep -oE '\[\[Category:[^]]+\]\]' "$FILE_PATH" | head -n 1 | sed 's/\[\[Category://;s/\]\]//' | tr ' ' '_')

if [ ! -z "$CATEGORY_EXTRACTED" ] && [ -f "$OUTPUT_DIR/Category_${CATEGORY_EXTRACTED}.txt" ]; then
    echo "📂 Category structural link found: Category:$CATEGORY_EXTRACTED. Including dependency..."
    cp "$OUTPUT_DIR/Category_${CATEGORY_EXTRACTED}.txt" "$HOST_STAGE_DIR/Category/${CATEGORY_EXTRACTED}.txt"
fi

sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
sudo docker cp "$HOST_STAGE_DIR" "${CONTAINER_NAME}:/var/www/html/maintenance/"

echo "📥 Injecting page updates into container array..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php importTextFiles.php \
    --prefix "" \
    --overwrite \
    "$CONTAINER_TARGET_DIR"/*.txt \
    "$CONTAINER_TARGET_DIR"/Category/*.txt 2>/dev/null || true

echo "🔄 Purging structural parser cache and updating lookups..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php refreshLinks.php --page "$TARGET_NPC" > /dev/null
if [ ! -z "$CATEGORY_EXTRACTED" ]; then
    # Refresh category tree indexing link arrays
    sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php refreshLinks.php --page "Category:${CATEGORY_EXTRACTED//_/ }" > /dev/null
fi
sudo docker exec -u www-data -i "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 > /dev/null

echo "🗑️ Clearing temporary single-run environments..."
sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
rm -rf "$HOST_STAGE_DIR"

echo "✅ Deployment complete! Check the live entries for '$TARGET_NPC' and its Category page."
