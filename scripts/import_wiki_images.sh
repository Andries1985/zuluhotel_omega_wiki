#!/bin/bash
# ==============================================================================
# Zuluhotel Omega Docker Wiki Image Importer
# ==============================================================================
# Description: Automatically copies and registers any local .png file inside
#              the input folder into the live Docker MediaWiki database.
# ==============================================================================

INPUT_DIR="$HOME/git/zuluhotel_omega_wiki/scripts/input"
CONTAINER_NAME="zuluhotelomega-wiki"

# Ensure there are actually PNG files to process
shopt -s nullglob
png_files=("$INPUT_DIR"/*.png)
shopt -u nullglob

if [ ${#png_files[@]} -eq 0 ]; then
    echo "ℹ️ No .png files found in $INPUT_DIR to import."
    exit 0
fi

echo "📸 Found ${#png_files[@]} image(s) targeting import array. Starting sequence..."

for file_path in "${png_files[@]}"; do
    file_name=$(basename "$file_path")
    echo "📦 Staging: $file_name"
    
    # 1. Copy the file directly into the container's temporary folder
    sudo docker cp "$file_path" "${CONTAINER_NAME}:/tmp/$file_name"
    
    # 2. Invoke the MediaWiki native image importer for this specific file
    echo "📥 Registering $file_name into MediaWiki database structures..."
    sudo docker exec -u www-data "$CONTAINER_NAME" \
        php /var/www/html/maintenance/run.php importImages.php /tmp \
        --extensions=png \
        --overwrite \
        --pattern="$file_name" > /dev/null
        
    # 3. Destroy the container's staging file to prevent ghost re-imports later
    sudo docker exec -it "$CONTAINER_NAME" rm -f "/tmp/$file_name"
    echo "✅ Successfully imported $file_name"
done

echo "🎉 Image registration batch complete! All media assets are now live."
