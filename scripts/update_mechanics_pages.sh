#!/bin/bash

# ==============================================================================
# ZULUHOTEL OMEGA WIKI - AUTOMATED MECHANICS INGESTION PIPELINE
# ==============================================================================

echo "🧼 Cleaning up local staging structures..."
rm -rf ~/wiki_import/*.txt

echo "⚙️ Running ETL Python parser script (Applying Animal Lore link fixes)..."
python3 ~/git/zuluhotel_omega_wiki/scripts/parse_mechanics_to_wiki.py

echo "📦 Synchronizing workspace files into the docker container staging layer..."
sudo docker exec -i zuluhotelomega-wiki rm -rf /var/www/html/maintenance/wiki_import
sudo docker exec -i zuluhotelomega-wiki mkdir -p /var/www/html/maintenance/wiki_import
sudo docker cp ~/wiki_import/. zuluhotelomega-wiki:/var/www/html/maintenance/wiki_import/

echo "🚀 Launching authenticated administrative deployment via Nagash..."
sudo docker exec -u www-data -i zuluhotelomega-wiki bash -c '
for file in /var/www/html/maintenance/wiki_import/*.txt; do
    [ -e "$file" ] || continue
    filename=$(basename "$file" .txt)
    title=$(echo "$filename" | sed "s/ & / and /g")

    echo "  -> Deploying page: $title"
    php /var/www/html/maintenance/run.php edit.php --user "Nagash" --summary "Automated Shard Mechanics pipeline update and link synchronization" "$title" < "$file"
done
'

echo "🗑️ Clearing down runtime container staging files..."
sudo docker exec -i zuluhotelomega-wiki rm -rf /var/www/html/maintenance/wiki_import
rm -rf ~/wiki_import

echo "✨ Flushing target parser caches directly..."
# Bypassing stdin blockages by passing /dev/null explicitly to the maintenance runner
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgePage.php "Main Page" < /dev/null
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgePage.php "Boat Commands" < /dev/null
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 < /dev/null

echo "✅ Deployment complete! Control returned safely to local system shell."
