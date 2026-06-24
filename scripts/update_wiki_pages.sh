#!/bin/bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Synchronizer Script (Modern Layout Compliant)
# ==============================================================================
# Recommended Pipeline Execution Sequence:
#   1. rm -rf output/*.txt
#   2. python3 parse_npcdesc_and_update_wiki.py
#   3. ./update_wiki_pages.sh
# ==============================================================================

OUTPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/output"
HOST_STAGE_DIR="$HOME/wiki_import"
CONTAINER_NAME="zuluhotelomega-wiki"
CONTAINER_TARGET_DIR="/var/www/html/maintenance/wiki_import"

if [ ! -f "$OUTPUT_DIR/current_npcs.list" ]; then
    echo "❌ Error: output/current_npcs.list is missing."
    echo "💡 Please ensure you execute the recommended 3-step pipeline sequence:"
    echo "   1. rm -rf output/*.txt"
    echo "   2. python3 parse_npcdesc_and_update_wiki.py"
    echo "   3. ./update_wiki_pages.sh"
    exit 1
fi

echo "🧽 Fetching all existing wiki pages from Category:NPCs using modern database layout..."
EXISTING_WIKI_PAGES=$(sudo docker exec -u www-data "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php sql.php \
    --query "SELECT cl_from FROM categorylinks JOIN linktarget ON cl_target_id = lt_id WHERE lt_namespace = 14 AND lt_title = 'NPCs';" | \
    grep -E '^[0-9]+$' | tr '\n' ',' | sed 's/,$//')

rm -f "$OUTPUT_DIR/to_delete.list"

if [ ! -z "$EXISTING_WIKI_PAGES" ]; then
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php sql.php \
        --query "SELECT page_title FROM page WHERE page_id IN ($EXISTING_WIKI_PAGES);" | \
        grep -v -E '(page_title|-----)' | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$OUTPUT_DIR/wiki_database_npcs.list"

    sort "$OUTPUT_DIR/wiki_database_npcs.list" > "$OUTPUT_DIR/db_sorted.tmp"
    sort "$OUTPUT_DIR/current_npcs.list" > "$OUTPUT_DIR/curr_sorted.tmp"
    comm -23 "$OUTPUT_DIR/db_sorted.tmp" "$OUTPUT_DIR/curr_sorted.tmp" > "$OUTPUT_DIR/to_delete.list"
    
    # Wipe targeted corrupt comma pages directly matching database configurations
    grep -E '^,' "$OUTPUT_DIR/wiki_database_npcs.list" >> "$OUTPUT_DIR/to_delete.list"
    
    sort -u "$OUTPUT_DIR/to_delete.list" -o "$OUTPUT_DIR/to_delete.list"
    rm -f "$OUTPUT_DIR/*.tmp" "$OUTPUT_DIR/wiki_database_npcs.list"
fi

if [ -s "$OUTPUT_DIR/to_delete.list" ]; then
    echo "🗑️ Found old/orphaned records on the live wiki database. Processing automated removals..."
    cat "$OUTPUT_DIR/to_delete.list" | while read -r old_page; do
        echo "   -> Dropping page: $old_page"
    done
    
    sudo docker cp "$OUTPUT_DIR/to_delete.list" "${CONTAINER_NAME}:/var/www/html/maintenance/"
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php deleteBatch.php \
        --r "Automated Sync: Profile asset removed or updated in master file configurations" \
        /var/www/html/maintenance/to_delete.list > /dev/null
    sudo docker exec -it "$CONTAINER_NAME" rm -f /var/www/html/maintenance/to_delete.list
else
    echo "🎉 Matrix environment clean! No obsolete assets detected for deletion."
fi
rm -f "$OUTPUT_DIR/to_delete.list"

echo "📦 Transferring updated dataset to temporary runtime environment..."
rm -rf "$HOST_STAGE_DIR"
mkdir -p "$HOST_STAGE_DIR"
cp "$OUTPUT_DIR"/*.txt "$HOST_STAGE_DIR/"

sudo docker cp "$HOST_STAGE_DIR" "${CONTAINER_NAME}:/var/www/html/maintenance/"

echo "📥 Launching bulk text payload injection array..."
sudo docker exec -u www-data -it "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php importTextFiles.php \
    --prefix "" \
    --overwrite \
    "$CONTAINER_TARGET_DIR"/*.txt

echo "🔄 Purging cache configurations and rebuilding relational search trees..."
sudo docker exec -u www-data -it "$CONTAINER_NAME" php /var/www/html/maintenance/run.php refreshLinks.php --all > /dev/null
sudo docker exec -u www-data -it "$CONTAINER_NAME" php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 > /dev/null

echo "🗑️ Clearing secondary temporary system file paths..."
sudo docker exec -it "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
rm -rf "$HOST_STAGE_DIR"

echo "✅ Optimization Sequence complete. All wiki components updated cleanly."

