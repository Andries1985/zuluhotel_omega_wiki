#!/bin/bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Synchronizer Script (CategoryTree Cache Variant)
# ==============================================================================

OUTPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/output"
HOST_STAGE_DIR="$HOME/wiki_import"
CONTAINER_NAME="zuluhotelomega-wiki"
CONTAINER_TARGET_DIR="/var/www/html/maintenance/wiki_import"

if [ ! -f "$OUTPUT_DIR/current_npcs.list" ]; then
    echo "❌ Error: output/current_npcs.list is missing."
    exit 1
fi

# Build master tracker manifest
cp "$OUTPUT_DIR/current_npcs.list" "$OUTPUT_DIR/current_total_manifest.tmp"
for cat_file in "$OUTPUT_DIR"/Category:*.txt; do
    if [ -e "$cat_file" ]; then
        cat_page_title=$(basename "$cat_file" .txt)
        echo "$cat_page_title" >> "$OUTPUT_DIR/current_total_manifest.tmp"
    fi
done

echo "🧽 Auditing workspace to purge legacy main-namespace clutter..."
sudo docker exec -u www-data "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php sql.php \
    --query "SELECT page_title FROM page WHERE page_namespace = 0 AND page_title LIKE 'Category%';" | \
    grep -v -E '(page_title|-----)' | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$OUTPUT_DIR/to_delete.list"

# Standard deletion check against Category leaks
EXISTING_WIKI_PAGES=$(sudo docker exec -u www-data "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php sql.php \
    --query "SELECT cl_from FROM categorylinks JOIN linktarget ON cl_target_id = lt_id WHERE lt_namespace = 14 AND lt_title = 'NPCs';" | \
    grep -E '^[0-9]+$' | tr '\n' ',' | sed 's/,$//')

if [ ! -z "$EXISTING_WIKI_PAGES" ]; then
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php sql.php \
        --query "SELECT page_title, page_namespace FROM page WHERE page_id IN ($EXISTING_WIKI_PAGES);" | \
        grep -v -E '(page_title|-----)' | while read -r title ns; do
            if [ "$ns" = "14" ]; then
                echo "Category:$title" | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' >> "$OUTPUT_DIR/db_raw.tmp"
            else
                echo "$title" | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' >> "$OUTPUT_DIR/db_raw.tmp"
            fi
        done

    if [ -f "$OUTPUT_DIR/db_raw.tmp" ]; then
        sort "$OUTPUT_DIR/db_raw.tmp" > "$OUTPUT_DIR/db_sorted.tmp"
        sort "$OUTPUT_DIR/current_total_manifest.tmp" > "$OUTPUT_DIR/curr_sorted.tmp"
        comm -23 "$OUTPUT_DIR/db_sorted.tmp" "$OUTPUT_DIR/current_total_manifest.tmp" >> "$OUTPUT_DIR/to_delete.list" 2>/dev/null || true
        rm -f "$OUTPUT_DIR"/*.tmp
    fi
fi

if [ -s "$OUTPUT_DIR/to_delete.list" ]; then
    sort -u "$OUTPUT_DIR/to_delete.list" -o "$OUTPUT_DIR/to_delete.list"
    echo "🗑️ Wiping out orphaned profiles and broken namespace items..."
    sudo docker cp "$OUTPUT_DIR/to_delete.list" "${CONTAINER_NAME}:/var/www/html/maintenance/delete_manifest.list"
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php deleteBatch.php \
        --r "Sync Cleanup: Automated structural integrity purge" \
        /var/www/html/maintenance/delete_manifest.list > /dev/null
    sudo docker exec -i "$CONTAINER_NAME" rm -f /var/www/html/maintenance/delete_manifest.list
fi
rm -f "$OUTPUT_DIR/to_delete.list" "$OUTPUT_DIR/current_total_manifest.tmp"

echo "📦 Transferring pristine datasets directly into Container workspace..."
rm -rf "$HOST_STAGE_DIR"
mkdir -p "$HOST_STAGE_DIR"
cp "$OUTPUT_DIR"/*.txt "$HOST_STAGE_DIR/"

sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
sudo docker cp "$HOST_STAGE_DIR" "${CONTAINER_NAME}:$CONTAINER_TARGET_DIR"

echo "📥 Launching text payload execution matrix..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" \
    php /var/www/html/maintenance/run.php importTextFiles.php \
    --prefix "" \
    --overwrite \
    "$CONTAINER_TARGET_DIR"/*.txt > /dev/null

echo "🔄 Executing Category link updates and structural syncs..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php refreshLinks.php --namespace 14 > /dev/null

echo "⚙️ Flushing backlogged system jobs..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php runJobs.php > /dev/null

echo "🚀 Evicting cache layers to live-update the Main Page layout..."
sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php purgePage.php "Main Page" > /dev/null
sudo docker exec -u www-data -i "$CONTAINER_NAME" php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 > /dev/null

echo "🗑️ Clearing staging environments..."
sudo docker exec -i "$CONTAINER_NAME" rm -rf "$CONTAINER_TARGET_DIR"
rm -rf "$HOST_STAGE_DIR"

echo "✅ Success! CategoryTree dropdown menus have fully refreshed."
