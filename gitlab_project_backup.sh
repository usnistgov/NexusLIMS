#!/usr/bin/env bash

# ------------------------------------------------------------------
# [Author: Joshua Taillon <***REMOVED***>]
#
#   NexusMicroscopyLIMS Gitlab Backup
#
#   This script will use the Gitlab API to initiate a backup of the
#   NexusMicroscopyLIMS project and save the downloaded repository
#   to the current directory following the Gitlab naming conventions.
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT="gitlab_nexuslims_backup"
LOG_FILE="gitlab_backup.log"
PROJECT_URL="https://***REMOVED***/api/v4/projects/676"

function log() {
    if [[ ${HIDE_LOG} ]]; then
        echo -e "[`date +"%Y/%m/%d:%H:%M:%S %z"`] $@" >> ${LOG_FILE}
    else
        echo -e "[`date +"%Y/%m/%d:%H:%M:%S %z"`] $@" | tee -a ${LOG_FILE}
    fi
}

function usage {
    echo "usage: ${0} [-hv] [-t token]"
    echo "  -h      display help"
    echo "  -v      display version"
    echo "  -q      quiet operation - does not print log to console"
    echo "  -t token   A Gitlab personal access token with API access"
    echo ""
}

function added_help {
    echo "This script will initiate and download a backup of the "
    echo "NexusMicroscopyLIMS Gitlab project using the Gitlab API. A personal"
    echo "access token with full API access must be supplied for authentication"
    echo "and can be created at: "
    echo ""
    echo "    https://***REMOVED***profile/personal_access_tokens"
    echo ""
}

function check_jq {
    if hash jq 2>/dev/null; then
        :
    else
        echo "This script requires jq to be installed and on the path."
        echo "More info: https://stedolan.github.io/jq/"
        echo ""
        echo "Please install using your package manager: "
        echo "i.e. \`sudo apt install jq\` or \`sudo pacman -Sy jq\`"
        echo ""
        exit 1
    fi
}

# --- Options processing -------------------------------------------
if [[ $# == 0 ]] ; then
    usage
    exit 1;
fi

while getopts ":t:qvh" optname
  do
    case "$optname" in
      "q")
        HIDE_LOG="true"
        ;;
      "v")
        echo "Version $VERSION"
        exit 0;
        ;;
      "t")
        token=${OPTARG}
        ;;
      "h")
        usage
        added_help
        exit 0;
        ;;
      "?")
        echo "Unknown option $OPTARG"
        exit 0;
        ;;
      ":")
        echo "No argument value for option $OPTARG"
        exit 0;
        ;;
      *)
        echo "Unknown error while processing options"
        exit 0;
        ;;
    esac
  done

shift $(($OPTIND - 1))

# --- Locks -------------------------------------------------------
LOCK_FILE=/tmp/${SUBJECT}.lock

if [[ -f "$LOCK_FILE" ]]; then
   echo "Script is already running"
   exit
fi

trap "rm -f ${LOCK_FILE}" EXIT
touch ${LOCK_FILE}

# --- Body --------------------------------------------------------

check_jq

# can use the log function as follows:
# log "[I] testing logging with token = ${token}"
log "-------------------------------------------"
log "[I] Running ${0}"

# POST request to start a backup:

# a 202 response was successful; a 401 is unauthorized
resp=$(curl -s --request POST --header "PRIVATE-TOKEN:${token}" ${PROJECT_URL}"/export")
log "[I] backup post response: ${resp}"

# check if POST was successful:
if echo ${resp} | jq '.message|contains("202")' | grep -q 'true'; then
    :
else
    echo "ERROR: There was an error initiating the export request. Please check"
    echo "the validity of the supplied access token and try again."
    exit 1
fi

COMPLETED="false"
# Wait a small while and check to see if export is finished:
for i in {1..100}
do
    sleep 1s   # sleep for 1 second to wait for export to finish
    # get export status:
    resp=$(curl -s --header "PRIVATE-TOKEN:${token}" ${PROJECT_URL}"/export")
    log "[I] [${i}/100] backup status response: ${resp}"
    if echo ${resp} | jq '.export_status|contains("started")' | grep -q 'true'; then
        # export has not completed yet, so continue to wait
        log "[I] [${i}/100] backup still processing"
        continue
    elif echo ${resp} | jq '.export_status|contains("finished")' | grep -q 'true'; then
        # export has finished, so break out of this loop
        log "[I] [${i}/100] backup finished!"
        COMPLETED="true"
        break
    else
        log "[W] [${i}/100] backup status is unknown... will try again"
    fi
done

if [[ "${COMPLETED}" == "false" ]]; then
    log "[E] backup did not finish processing in allowed number of iterations, please"
    log "[E] wait for the email from Gitlab and download the exported project manually"
else
    # use curl to download the completed backup to the current directory
    resp=$(curl -OJL --header "PRIVATE-TOKEN:${token}" ${PROJECT_URL}"/export/download")
    log "[I] backup download response: ${resp}"
fi

# move backups into sub-folder:
FOLDER=backups
mkdir -p ${FOLDER}
for file in *export.tar.gz
do
    log "[I] Moving ${file} to ${FOLDER}"
    mv ${file} ${FOLDER}
done

# -----------------------------------------------------------------