#!/bin/bash

# getoptでオプションを解析
OPTIONS=$(getopt -o dr -- "$@")
if [ $? != 0 ]; then
    echo "Failed to parse options." >&2
    exit 1
fi

eval set -- "$OPTIONS"

# 初期値設定
RETRY=""
DRY_RUN=false
DIRECTORY="."

# オプション処理
while true; do
    case "$1" in
        -d)
            DRY_RUN=true
            shift
            ;;
        -r)
            RETRY="-r"
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
done

# 引数が残っている場合、それをディレクトリとして使用
if [ $# -gt 0 ]; then
    DIRECTORY=$1
fi

# "_shrunk.jpeg" を含まない JPEG ファイルについてのみ実行
find "$DIRECTORY" -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) \
     -not -name "*_shrunk.jpeg" | while read -r file; do
    
    # Dry run モードの場合はコマンドをエコー
    if [ "$DRY_RUN" = true ]; then
        echo "Dry run: ./image_uploader.py -f \"$file\" $RETRY"
    else
        # 実行モードの場合は image_uploader.py を実行
        ./image_uploader.py -f "$file" $RETRY
    fi
done
