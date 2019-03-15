#!/usr/bin/env bash

# ------------------------------------------------------------------
# [Author: Joshua Taillon <***REMOVED***>]
#
#   Gitlab Backup Script
#
#   This script will use the Gitlab API to initiate a backup of the
#   a NIST Gitlab project and save the downloaded repository
#   to the current directory following the Gitlab naming conventions.
# ------------------------------------------------------------------

VERSION=0.1.1
SUBJECT="gitlab_backup"
LOG_FILE="gitlab_backup.log"
PROJECT_URL="https://***REMOVED***/api/v4/projects"

function log() {
    if [[ ${HIDE_LOG} ]]; then
        echo -e "[`date +"%Y/%m/%d:%H:%M:%S %z"`] $@" >> ${LOG_FILE}
    else
        echo -e "[`date +"%Y/%m/%d:%H:%M:%S %z"`] $@" | tee -a ${LOG_FILE}
    fi
}

function usage {
    echo "usage: ${0} [-hv] [-t token] [-n project_id]"
    echo "  -t token        a Gitlab personal access token with API access      (required)"
    echo "  -n project_id   a Gitlab project id number                          (required)"
    echo "  -q              quiet operation - does not print log to console     (optional)"
    echo "  -h              display detailed help"
    echo "  -v              display version"
    echo ""
}

function added_help {
    echo "This script will initiate and download a backup of the "
    echo "NIST Gitlab project using the Gitlab API. The project ID is a"
    echo "numeric value, and can be found on the project homepage underneath"
    echo "the project name and next to the avatar image."
    echo ""
    echo "A personal access token with full API access must also be supplied"
    echo "for authentication and can be created at: "
    echo ""
    echo "    https://***REMOVED***profile/personal_access_tokens"
    echo ""
    echo "Finally, this tool requires the jq tool for parsing json, so please"
    echo "ensure that is installed before running the script."
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

while getopts ":n:t:qvh" optname
  do
    case "$optname" in
      "q")
        HIDE_LOG="true"
        ;;
      "v")
        echo "Version $VERSION"
        exit 0;
        ;;
      "n")
        project_id=${OPTARG}
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

# Check to make sure mandatory "options" are supplied
if [[ -z ${project_id} ]] || [[ -z ${token} ]]
then
    log "[E] Both -n and -t options must be supplied for this script to run"
    echo ""
    usage
    exit 1
fi

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

EXPORT_URL=${PROJECT_URL}"/"${project_id}"/export"


# POST request to start a backup:
resp=$(curl -s --request POST --header "PRIVATE-TOKEN:${token}" ${EXPORT_URL})
log "[I] backup post response: ${resp}"

# check if POST was successful:
# a 202 response was successful; a 401 is unauthorized; 403 is forbidden
if echo ${resp} | jq '.error|contains("404")' 2> /dev/null | grep -q 'true'; then
    log "[E] Something has gone wrong; request path was invalid"
    exit 1
elif echo ${resp} | jq '.message|contains("401")' 2> /dev/null | grep -q 'true'; then
    log "[E] There was an error authenticating with the supplied access token."
    log "[E] Please check that it is correct and try again."
    exit 1
elif echo ${resp} | jq '.message|contains("403")' 2> /dev/null | grep -q 'true'; then
    log "[E] The supplied access token is not authorized to access the"
    log "[E] project ID: ${project_id}. Please check both values and try again."
    exit 1
elif echo ${resp} | jq '.message|contains("202")' 2> /dev/null | grep -q 'true'; then
    :
else
    log "[E] There was an error initiating the export request. Please check"
    log "[E] the validity of the supplied access token and project ID and try again."
    exit 1
fi

COMPLETED="false"
# Wait a small while and check to see if export is finished:
for i in {1..100}
do
    sleep 1s   # sleep for 1 second to wait for export to finish
    # get export status:
    resp=$(curl -s --header "PRIVATE-TOKEN:${token}" ${EXPORT_URL})
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
    resp=$(curl -OJL --header "PRIVATE-TOKEN:${token}" ${EXPORT_URL}"/download")
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