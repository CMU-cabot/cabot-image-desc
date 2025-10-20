#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/heic_directory"
    exit 1
fi

INPUT_DIR="$1"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory '$INPUT_DIR' does not exist."
    exit 1
fi

OUTPUT_DIR="$INPUT_DIR/converted"
mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.HEIC "$INPUT_DIR"/*.heic; do
    [ -e "$file" ] || continue

    base=$(basename "$file" .HEIC)
    base=$(basename "$base" .heic)
    tmpfile="$OUTPUT_DIR/${base}_tmp.jpg"
    outfile="$OUTPUT_DIR/${base}.jpg"

    echo "🔄 Converting: $file → $outfile"

    if ! heif-convert "$file" "$tmpfile" > /dev/null; then
        echo "❌ heif-convert failed for $file"
        continue
    fi

    if ! exiftool -TagsFromFile "$file" -overwrite_original "$tmpfile" > /dev/null; then
        echo "⚠️  exiftool failed for $file"
    fi

    mv "$tmpfile" "$outfile"

    echo "✅
