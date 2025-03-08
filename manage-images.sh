#!/usr/bin/env bash


function err {
    >&2 red "[ERROR] "$@
}
function red {
    echo -en "\033[31m"  ## red
    echo $@
    echo -en "\033[0m"  ## reset color
}
function blue {
    echo -en "\033[36m"  ## blue
    echo $@
    echo -en "\033[0m"  ## reset color
}
function snore()
{
    local IFS
    [[ -n "${_snore_fd:-}" ]] || exec {_snore_fd}<> <(:)
    read ${1:+-t "$1"} -u $_snore_fd || :
}
function help() {
    echo "Usage: "
    echo "  $0 [options]"
    echo "  Examples:"
    echo "   $0 -i image.jpg"
    echo "   $0 -I /path/to/images       # upload all images in the directory"
    echo ""
    echo "  -d              : Development mode"
    echo "  -c              : Clear all tags"
    echo "  -e              : Check EXIF"
    echo "  -F <floor>      : Specify the floor of the image"
    echo "  -h              : Show this help"
    echo "  -i <imagefile>  : Specify an image file to upload"
    echo "  -I <directory>  : Specify the directory to upload images"
    echo "  -j              : Show JSON data of the image; works with -i"
    echo "  -J <jsonid>     : Specify the JSON ID to show"
    echo "  -l              : List all images"
    echo "  -n              : Dry run mode"
    echo "  -p <promptfile> : Specify the prompt file"
    echo "  -r              : Retry mode"
    echo "  -R <jsonid>     : Remove the JSON ID"
    echo "  -t <tag>        : add a tag, you can specify multiple tags like -t tag1 -t tag2"
    echo "  -T <tag>        : remove a tag, you can specify multiple tags like -T tag1 -T tag2"
    echo "  -P <json>       : import JSON images"
    echo "  -X <json>       : export JSON images"
    exit 1
}

DEBUG=
PROFILE=prod
IMAGE=
DIRECTORY=
PROMPT=./default-prompt.txt
PROMPT_OPTION=
EXIF=
FLOOR=
DRY_RUN=
RETRY=
LIST=
JSON=
TAGS=
IMPORT=
EXPORT=

while getopts "cdeF:hI:i:J:jlnp:R:rt:T:P:X:" OPT; do
    case $OPT in
        c)
            TAGS="-c"
            ;;
        d)
            PROFILE=dev
            DEBUG=true
            ;;
        e)
            EXIF="-e"
            ;;
        F)
            FLOOR="-F $OPTARG"
            ;;
        h)
            help
            ;;
        I)
            DIRECTORY=$OPTARG
            ;;
        i)
            IMAGE=$OPTARG
            ;;
        J)
            JSON="-J $OPTARG"
            ;;
        j)
            JSON="-j"
            ;;
        l)
            LIST="-l"
            ;;
        n)
            DRY_RUN="-n"
            ;;
        p)
            PROMPT=$OPTARG
            PROMPT_OPTION="-p /tmp/prompt.txt"
            ;;
        R)
            JSON="-R $OPTARG"
            ;;
        r)
            RETRY="-r"
            ;;
        t)
            TAGS="-t $OPTARG $TAGS"
            ;;
        T)
            TAGS="-T $OPTARG $TAGS"
            ;;
        P)
            IMPORT=$OPTARG
            ;;
        X)
            EXPORT=$OPTARG
            ;;
        *)
            echo "Invalid option"
            help
            ;;
    esac
done

if $DEBUG; then
    echo "PROFILE: $PROFILE"
    echo "IMAGE: $IMAGE"
    echo "DIRECTORY: $DIRECTORY"
    echo "PROMPT: $PROMPT"
    echo "EXIF: $EXIF"
    echo "FLOOR: $FLOOR"
    echo "DRY_RUN: $DRY_RUN"
    echo "RETRY: $RETRY"
    echo "LIST: $LIST"
    echo "JSON: $JSON"
    echo "TAGS: $TAGS"
    echo "IMPORT: $IMPORT"
    echo "EXPORT: $EXPORT"
fi

function upload_image() {
    local image=$(realpath $1)

    if [[ -z $image ]]; then
        docker compose run --rm image_desc-upload-$PROFILE bash -c \
            "./image_uploader.py $JSON $LIST"
        return
    fi

    image_name=$(basename $image)
    prompt=$(realpath $PROMPT)

    blue "Uploading $image"

    docker compose run --rm \
      -v $image:/tmp/$image_name \
      -v $prompt:/tmp/prompt.txt \
      image_desc-upload-$PROFILE bash -c \
      "./image_uploader.py -f /tmp/$image_name $RETRY $DRY_RUN $EXIF $PROMPT_OPTION $FLOOR $LIST $JSON $TAGS"
}

if [[ -n $EXPORT ]]; then
    if [[ -e $EXPORT ]]; then
        err "File already exists: $EXPORT"
        exit 1
    fi
    tempdir=$(mktemp -d)
    docker compose run --rm \
      -v $tempdir:/tmp \
      image_desc-upload-$PROFILE bash -c \
        "./export_data.py /tmp/export.json"
    cp $tempdir/export.json $EXPORT
elif [[ -n $IMPORT ]]; then
    if [[ ! -e $IMPORT ]]; then
        err "File not found: $IMPORT"
        exit 1
    fi
    docker compose run --rm \
      -v $(realpath $IMPORT):/tmp/import.json \
      image_desc-upload-$PROFILE bash -c \
        "./import_data.py /tmp/import.json"
elif [[ -n $IMAGE ]] || [[ -n $JSON ]] || [[ -n $LIST ]]; then
    upload_image $IMAGE
elif [[ -n $DIRECTORY ]]; then
    files=$(find $DIRECTORY -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -not -name "*_shrunk.jpeg")
    for file in $files; do
        upload_image $file
    done
else
    echo "Either -i or -I option is required"
    help
fi
