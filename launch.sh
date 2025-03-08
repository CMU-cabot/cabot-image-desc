#!/bin/bash

stop_launch() {
    docker compose -f $dcfile $profile down
    exit 0
}

trap 'stop_launch' SIGINT SIGTERM

pwd=`pwd`
scriptdir=`dirname $0`
cd $scriptdir
scriptdir=`pwd`
prefix=$(basename `pwd`)

function help {
    echo "Usage: $0"
    echo ""
    echo "-h           show this help"
    echo "-d           development launch"
}

development=0
dcfile=docker-compose.yaml

while getopts "hd" arg; do
    case $arg in
    h)
        help
        exit
        ;;
    d)
        development=1
        ;;
    esac
done
shift $((OPTIND-1))

log_prefix=cabot-image-desc
log_name=${log_prefix}_`date +%Y-%m-%d-%H-%M-%S`

source $scriptdir/.env

if [ -n "$CABOT_LAUNCH_DEV_PROFILE" ]; then
    development=$CABOT_LAUNCH_DEV_PROFILE
fi

profile="--profile prod"
if [[ $development -eq 1 ]]; then
    profile="--profile dev"
fi
com="docker compose -f $dcfile $profile up 2>&1 | tee logs/$log_name.log"

echo $com
eval $com
