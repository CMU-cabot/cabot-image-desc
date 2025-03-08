#!/bin/bash

# Copyright (c) 2024  Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

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
    echo "-t           run test with mock OpenAI APIs"
    echo "-o           run test with actual OpenAI APIs"
    echo "-l           run lint test"
    echo "-v           verbose mode"
}

profile=prod
dcfile=docker-compose.yaml

while getopts "hdtolv" arg; do
    case $arg in
    h)
        help
        exit
        ;;
    d)
        profile=dev
        ;;
    t)
        profile=test
        ;;
    o)
        profile=openai
        ;;
    l)
        profile=lint
        ;;
    v)
        export VERBOSE_OUTPUT=true
        ;;
    *)
        echo "Invalid option: -$OPTARG" >&2
        help
        exit 1
        ;;
    esac
done
shift $((OPTIND-1))

log_prefix=cabot-image-desc
log_name=${log_prefix}_`date +%Y-%m-%d-%H-%M-%S`

source $scriptdir/.env

if [[ -n "$CABOT_LAUNCH_DEV_PROFILE" ]] && [[ $profile = "prod" ]];  then
    profile=dev
fi

com="docker compose -f $dcfile --profile ${profile} up 2>&1 | tee logs/$log_name.log"

echo $com
eval $com
