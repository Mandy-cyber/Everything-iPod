#!/bin/bash

# extract album art to local Music directory
echo "=================================================================="
echo "Extracting album art..."
python3 album_art_fixer.py $1 > /dev/null
echo -e "Finished extracting album art\n"

# setup
COVER_NAME="cover.jpg"
num_albums=0
num_missing=0
echo "Missing album covers for:"

# check for missing album covers
while read -r album_dir; do
    ((num_albums++))

    if [ -f "$album_dir/$COVER_NAME" ]; then
        # it exists
        continue
    else
        # missing
        ((num_missing++))
        echo "  $album_dir"
    fi
done < <(find ~/Music -mindepth 2 -maxdepth 2 -type d)

if (( num_missing == 0 )); then
    echo "None! Continuing."
fi

echo -e "\n*** FYI You have a total of $num_albums albums saved."
echo -e "==================================================================\n"

# sync local Music directory with iPOD Music directory
echo "Starting sync with iPod..."
rsync -avh --progress \
    --include="*.flac" \
    --include="*.mp3" \
    --include="*/" \
    --exclude="*" \
    $1 $2