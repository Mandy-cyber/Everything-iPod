#!/bin/bash

# sync local Music directory with iPOD Music directory
rsync -avh --progress \
    --include="*.flac" \
    --include="*.mp3" \
    --include="*/" \
    --exclude="*" \
    $1 $2