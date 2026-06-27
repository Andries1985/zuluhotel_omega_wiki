#!/usr/bin/env bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Synchronizer - Single Page Deployment Variant
# ==============================================================================
# Usage:
#   ./update_single_page.sh <npctemplate_id>
#
# Examples:
#   ./update_single_page.sh alligator
#   ./update_single_page.sh cavedragon
#   ./update_single_page.sh "cave dragon"
# ==============================================================================

set -e

OUTPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/output"
HOST_STAGE_DIR="$HOME/wiki_import_single"
CONTAINER_NAME="zuluhotelomega-wiki"
CONTAINER_TARGET_DIR="/var/www/html/maintenance/wiki_import_single"

# Read argument value or fall back cleanly to default alligator reference
TARGET_ARG="${1:-alligator}"

# Clean the search argument (lowercase and strip spaces/underscores)
CLEAN_ARG=$(echo "$TARGET_ARG" | tr '[:upper:]' '[:lower:]' | tr -d ' _')

# Robust search: Scan text payloads, stripping spaces/underscores for comparison
FILE_PATH=""
for file in "$OUTPUT_DIR"/*.txt; do
    [ -e "$file" ] || continue
    base_name=$(basename "$file" .txt)
    clean_file=$(echo "$base_name" | tr '[:upper:]' '[:lower:]' | tr -d ' _')
    
    if [ "$clean_file" = "$CLEAN_ARG" ]; then
        FILE_PATH="$file"
        break
    fi
done

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    echo "❌ Error: Expected parsed text payload file for '$TARGET_ARG' is missing in output directory."
    echo "💡 Please ensure you execute the configuration compiler first:"
    echo "   python3 test_parse_npc.py $TARGET_ARG"
    exit 1
fi

TARGET_NPC=$(basename "$FILE_PATH" .txt)
echo "🚀 Isolated Sync initiated for script template reference: [$TARGET_ARG] -> ($TARGET_NPC)"

echo "📦 Preparing localized staging directory..."
rm -rf "$HOST_STAGE_DIR"
mkdir -p "$HOST_STAGE_DIR"
cp "$FILE_PATH" "$HOST_STAGE_DIR/"

sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
sudo docker cp "$HOST_STAGE_DIR" "${CONTAINER_NAME}:/var/www/html/maintenance/"

echo "📥 Injecting page updates into container array..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php importTextFiles.php \
    --prefix "" \
    --overwrite \
    "$CONTAINER_TARGET_DIR"/*.txt

echo "🔄 Purging structural parser cache for current asset viewports..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 > /dev/null

echo "🗑️ Clearing temporary single-run environments..."
sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
rm -rf "$HOST_STAGE_DIR"

echo "✅ Deployment complete! Check the live entry for '$TARGET_NPC' on your wiki."
