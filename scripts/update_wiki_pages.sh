#!/bin/bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Synchronizer Script (Stubborn Comma Purge Edition)
# ==============================================================================

OUTPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/output"
HOST_STAGE_DIR="$HOME/wiki_import"
CONTAINER_NAME="zuluhotelomega-wiki"
CONTAINER_TARGET_DIR="/var/www/html/maintenance/wiki_import"

if [ ! -f "$OUTPUT_DIR/current_npcs.list" ]; then
    echo "❌ Error: output/current_npcs.list is missing. Please run python3 first!"
    exit 1
fi

echo "🧽 Fetching all existing wiki pages from Category:NPCs using modern database layout..."
# MediaWiki 1.44+ schema normalization query utilizing linktarget and categorylinks
EXISTING_WIKI_PAGES=$(sudo docker exec -u www-data "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php sql.php \
    --query "SELECT cl_from FROM categorylinks JOIN linktarget ON cl_target_id = lt_id WHERE lt_namespace = 14 AND lt_title = 'NPCs';" | \
    grep -E '^[0-9]+$' | tr '\n' ',' | sed 's/,$//')

# Clear old deletion manifests
rm -f "$OUTPUT_DIR/to_delete.list"

if [ ! -z "$EXISTING_WIKI_PAGES" ]; then
    # Parse modern titles from database matching tracking sets
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php sql.php \
        --query "SELECT page_title FROM page WHERE page_id IN ($EXISTING_WIKI_PAGES);" | \
        grep -v -E '(page_title|-----)' | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$OUTPUT_DIR/wiki_database_npcs.list"

    # Compare current state profiles against live databases
    sort "$OUTPUT_DIR/wiki_database_npcs.list" > "$OUTPUT_DIR/db_sorted.tmp"
    sort "$OUTPUT_DIR/current_npcs.list" > "$OUTPUT_DIR/curr_sorted.tmp"
    comm -23 "$OUTPUT_DIR/db_sorted.tmp" "$OUTPUT_DIR/curr_sorted.tmp" > "$OUTPUT_DIR/to_delete.list"
    
    # HARD PURGE EXTRA: Forcefully locate any orphan titles in the database list that start with a comma
    # and add them explicitly to the deletion list to solve the "image_e9a435.png" issue.
    grep -E '^,' "$OUTPUT_DIR/wiki_database_npcs.list" >> "$OUTPUT_DIR/to_delete.list"
    
    # Sort and clean up duplicates from the deletion list
    sort -u "$OUTPUT_DIR/to_delete.list" -o "$OUTPUT_DIR/to_delete.list"
    rm -f "$OUTPUT_DIR/*.tmp" "$OUTPUT_DIR/wiki_database_npcs.list"
fi

# Execute automated batch deletion rules if mismatched configurations exist
if [ -s "$OUTPUT_DIR/to_delete.list" ]; then
    echo "🗑️ Found old/orphaned records on the live wiki database. Processing automated removals..."
    cat "$OUTPUT_DIR/to_delete.list" | while read -r old_page; do
        echo "   -> Dropping page: $old_page"
    done
    
    sudo docker cp "$OUTPUT_DIR/to_delete.list" "${CONTAINER_NAME}:/var/www/html/maintenance/"
    
    # Use deleteBatch.php to wipe the targets completely
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php deleteBatch.php \
        --r "Automated Sync: Cleaning up corrupt comma-prefixed ghost pages" \
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
