#!/bin/bash

# ==============================================================================
# ZULUHOTEL OMEGA WIKI - AUTOMATED SKILLS INGESTION PIPELINE
# ==============================================================================

echo "🧼 Cleaning up local skills staging structures..."
rm -rf ~/wiki_import/*.txt

echo "⚙️ Running ETL Python parser script for Shard Skills..."
python3 ~/git/zuluhotel_omega_wiki/scripts/parse_skills_to_wiki.py

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
    php /var/www/html/maintenance/run.php edit.php --user "Nagash" --summary "Automated Skills pipeline update" "$title" < "$file"
done
'

echo "🗑️ Clearing down runtime container staging files..."
sudo docker exec -i zuluhotelomega-wiki rm -rf /var/www/html/maintenance/wiki_import
rm -rf ~/wiki_import

echo "✨ Flushing target parser caches directly..."
# Explicitly piping /dev/null breaks down the standard input streams to avoid CLI stalls
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgePage.php "Main Page" < /dev/null
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgePage.php "Skills" < /dev/null
sudo docker exec -u www-data -i zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgeParserCache.php --age 0 < /dev/null

echo "✅ Deployment complete! Control returned safely to local system shell."
