#!/bin/bash

# =====================================================================
# 1. Inject structural Category tags into the Markdown files first
# =====================================================================
echo "Injecting categories based on directory structures..."
cd ~/git/zuluhotelomega-website/content/infovault

OPEN_BRACKETS="[["
CLOSE_BRACKETS="]]"

for dir in classes items misc npcs resources skills; do
    if [ -d "$dir" ]; then
        if [ "$dir" = "npcs" ]; then
            category="NPCs"
        else
            # Native Bash capitalization: No tr command or single quotes to break Vim!
            category="${dir^}"
        fi
        
        echo "Processing category: Category:$category"
        
        find "$dir" -type f -name "*.md" | while read -r FILE; do
            SEARCH="Category:${category}"
            if ! grep -qF "${SEARCH}" "${FILE}"; then
                TAG_STRING="${OPEN_BRACKETS}Category:${category}${CLOSE_BRACKETS}"
                echo -e "\n\n${TAG_STRING}" >> "${FILE}"
            fi
        done
    fi
done

# Jump back to content directory for the rest of your original script
cd ~/git/zuluhotelomega-website/content

# =====================================================================
# 2. Your Original Data Conversion & Import Pipeline
# =====================================================================
echo "Clearing out old scratch arrays from earlier compilation passes..."
rm -f temp_*.md *.txt

echo "Running your data parser script..."
python3 convert_hugo.py

echo "Staging compiled documentation text files..."
mkdir -p ~/wiki_import && cp *.txt ~/wiki_import/

echo "Synchronizing data into your target Docker engine volume layout..."
sudo docker cp ~/wiki_import zuluhotelomega-wiki:/var/www/html/maintenance/

echo "Overwriting the main wiki contents directly..."
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php importTextFiles.php --prefix "" --overwrite /var/www/html/maintenance/wiki_import/*.txt

# =====================================================================
# 3. Missing Link Rebuild (Crucial for CategoryTree to populate)
# =====================================================================
echo "Rebuilding database link matrices for CategoryTree..."
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php refreshLinks.php

# =====================================================================
# 4. Cleanup
# =====================================================================
echo "Wiping out workspace files safely..."
sudo docker exec -it zuluhotelomega-wiki rm -rf /var/www/html/maintenance/wiki_import && rm -rf ~/wiki_import

echo "Wiki update complete!"
