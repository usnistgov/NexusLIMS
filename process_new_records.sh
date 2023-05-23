#!/usr/bin/env bash

# leans on a bash template from:
# https://github.com/ralish/bash-script-template/blob/stable/template.sh
# actual running code is in the main() function towards the bottom

# Uses ssmtp to send notification email if there's an error (must be configured
# on system running this script to send emails)

# Enable xtrace if the DEBUG environment variable is set
if [[ ${DEBUG-} =~ ^1|yes|true$ ]]; then
    set -o xtrace       # Trace the execution of the script (debug)
fi

# A better class of script...
set -o errexit          # Exit on most errors (see the manual)
set -o errtrace         # Make sure any error trap is inherited
set -o nounset          # Disallow expansion of unset variables
set -o pipefail         # Use last non-zero exit code in a pipeline

# DESC: Handler for unexpected errors
# ARGS: $1 (optional): Exit code (defaults to 1)
# OUTS: None
function script_trap_err() {
    local exit_code=1

    # Disable the error trap handler to prevent potential recursion
    trap - ERR

    # Consider any further errors non-fatal to ensure we run to completion
    set +o errexit
    set +o pipefail

    # Validate any provided exit code
    if [[ ${1-} =~ ^[0-9]+$ ]]; then
        exit_code="$1"
    fi

    # Output debug data if in Cron mode
    if [[ -n ${cron-} ]]; then
        # Restore original file output descriptors
        if [[ -n ${script_output-} ]]; then
            exec 1>&3 2>&4
        fi

        # Print basic debugging information
        printf '%b\n' "$ta_none"
        printf '***** Abnormal termination of script *****\n'
        printf 'Script Path:            %s\n' "$script_path"
        printf 'Script Parameters:      %s\n' "$script_params"
        printf 'Script Exit Code:       %s\n' "$exit_code"

        # Print the script log if we have it. It's possible we may not if we
        # failed before we even called cron_init(). This can happen if bad
        # parameters were passed to the script so we bailed out very early.
        if [[ -n ${script_output-} ]]; then
            printf 'Script Output:\n\n%s' "$(cat "$script_output")"
        else
            printf 'Script Output:          None (failed before log init)\n'
        fi
    fi

    # Exit with failure status
    exit "$exit_code"
}

# DESC: Handler for exiting the script
# ARGS: None
# OUTS: None
function script_trap_exit() {
    # test to see if we have any files/directories at all in nexusLIMS_path;
    # if we don't (i.e. the "find | wc -l" equals zero) then the mount point
    # is probably not set up correctly and we should bail and send an email warning
    if [[ $(find ${nexusLIMS_path} -maxdepth 0  | wc -l) -eq 0 ]]; then 
        echo "no files at all found"; 
        send_email 'no_log'
    else
        # delete lock file
        if [ -f "${LOCKFILE}" ] && [ "$WE_CREATED_LOCKFILE" = true ] ; then
            echo "Deleting lock file at ${LOCKFILE}" | tee -a "${LOGPATH}"
            rm "${LOCKFILE}"
        elif [ -f "${LOCKFILE}" ]; then
            echo "We didn't create lock file at ${LOCKFILE}; so leaving in place" | tee -a "${LOGPATH}"
        fi

        # parse logfile for any erorr and send email (regardless of what happened
        # in the script, since this happens in the exit trap)
        #if grep -q -i -E 'critical|error|exception|fatal|no_files_found' "${LOGPATH}"; then
        if grep -q -i -E 'critical|error|fatal' "${LOGPATH}"; then
        stringArr=()
        # do some more detailed checks to allow us to specify which text was
        # found in the output:
            if grep -q -i -E 'critical' "${LOGPATH}"; then
                stringArr+=("critical")
            elif grep -q -i -E 'error' "${LOGPATH}"; then
                stringArr+=("error")
            elif grep -q -i -E 'fatal' "${LOGPATH}"; then
                stringArr+=("fatal")
            elif grep -q -i -E 'no_files_found' "${LOGPATH}"; then
                stringArr+=("no_files_found")
            fi
            found_strings=$(IFS=, ; echo "${stringArr[*]}")
        
            # ignore (somewhat) common DNS issues and don't alert
            if grep -q -i -E "Temporary failure in name resolution" "${LOGPATH}"; then
                :
            elif grep -q -E "NoDataConsentError" "${LOGPATH}"; then
                # don't alert on NoDataConsentError
                :
            elif grep -q -E "NoMatchingReservationError" "${LOGPATH}"; then
                # don't alert on NoMatchingReservationError
                :
            else
                send_email 'dummy_param'
            fi
        else
        # do nothing
        :
        fi

        cd "$orig_cwd"

        # Remove Cron mode script log
        if [[ -n ${cron-} && -f ${script_output-} ]]; then
            rm "$script_output"
        fi

        # Remove script execution lock
        if [[ -d ${script_lock-} ]]; then
            rmdir "$script_lock"
        fi

        # Restore terminal colours
        printf '%b' "$ta_none"
    fi
}

# DESC: Exit script with the given message
# ARGS: $1 (required): Message to print on exit
#       $2 (optional): Exit code (defaults to 0)
# OUTS: None
# NOTE: The convention used in this script for exit codes is:
#       0: Normal exit
#       1: Abnormal exit due to external error
#       2: Abnormal exit due to script error
function script_exit() {
    if [[ $# -eq 1 ]]; then
        printf '%s\n' "$1"
        exit 0
    fi

    if [[ ${2-} =~ ^[0-9]+$ ]]; then
        printf '%b\n' "$1"
        # If we've been provided a non-zero exit code run the error trap
        if [[ $2 -ne 0 ]]; then
            script_trap_err "$2"
        else
            exit 0
        fi
    fi

    script_exit 'Missing required argument to script_exit()!' 2
}

# DESC: Generic script initialisation
# ARGS: $@ (optional): Arguments provided to the script
# OUTS: $orig_cwd: The current working directory when the script was run
#       $script_path: The full path to the script
#       $script_dir: The directory path of the script
#       $script_name: The file name of the script
#       $script_params: The original parameters provided to the script
#       $ta_none: The ANSI control code to reset all text attributes
# NOTE: $script_path only contains the path that was used to call the script
#       and will not resolve any symlinks which may be present in the path.
#       You can use a tool like realpath to obtain the "true" path. The same
#       caveat applies to both the $script_dir and $script_name variables.
# shellcheck disable=SC2034
function script_init() {
    # Useful paths
    readonly orig_cwd="$PWD"
    readonly script_path="${BASH_SOURCE[0]}"
    readonly script_dir="$(dirname "$script_path")"
    readonly script_name="$(basename "$script_path")"
    readonly script_params="$*"

    # Important to always set as we use it in the exit handler
    readonly ta_none="$(tput sgr0 2> /dev/null || true)"
}

# DESC: Initialise colour variables
# ARGS: None
# OUTS: Read-only variables with ANSI control codes
# NOTE: If --no-colour was set the variables will be empty
# shellcheck disable=SC2034
function colour_init() {
    if [[ -z ${no_colour-} ]]; then
        # Text attributes
        readonly ta_bold="$(tput bold 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly ta_uscore="$(tput smul 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly ta_blink="$(tput blink 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly ta_reverse="$(tput rev 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly ta_conceal="$(tput invis 2> /dev/null || true)"
        printf '%b' "$ta_none"

        # Foreground codes
        readonly fg_black="$(tput setaf 0 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_blue="$(tput setaf 4 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_cyan="$(tput setaf 6 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_green="$(tput setaf 2 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_magenta="$(tput setaf 5 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_red="$(tput setaf 1 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_white="$(tput setaf 7 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly fg_yellow="$(tput setaf 3 2> /dev/null || true)"
        printf '%b' "$ta_none"

        # Background codes
        readonly bg_black="$(tput setab 0 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_blue="$(tput setab 4 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_cyan="$(tput setab 6 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_green="$(tput setab 2 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_magenta="$(tput setab 5 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_red="$(tput setab 1 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_white="$(tput setab 7 2> /dev/null || true)"
        printf '%b' "$ta_none"
        readonly bg_yellow="$(tput setab 3 2> /dev/null || true)"
        printf '%b' "$ta_none"
    else
        # Text attributes
        readonly ta_bold=''
        readonly ta_uscore=''
        readonly ta_blink=''
        readonly ta_reverse=''
        readonly ta_conceal=''

        # Foreground codes
        readonly fg_black=''
        readonly fg_blue=''
        readonly fg_cyan=''
        readonly fg_green=''
        readonly fg_magenta=''
        readonly fg_red=''
        readonly fg_white=''
        readonly fg_yellow=''

        # Background codes
        readonly bg_black=''
        readonly bg_blue=''
        readonly bg_cyan=''
        readonly bg_green=''
        readonly bg_magenta=''
        readonly bg_red=''
        readonly bg_white=''
        readonly bg_yellow=''
    fi
}

# DESC: Pretty print the provided string
# ARGS: $1 (required): Message to print (defaults to a green foreground)
#       $2 (optional): Colour to print the message with. This can be an ANSI
#                      escape code or one of the prepopulated colour variables.
#       $3 (optional): Set to any value to not append a new line to the message
# OUTS: None
function pretty_print() {
    if [[ $# -lt 1 ]]; then
        script_exit 'Missing required argument to pretty_print()!' 2
    fi

    if [[ -z ${no_colour-} ]]; then
        if [[ -n ${2-} ]]; then
            printf '%b' "$2"
        else
            printf '%b' "$fg_green"
        fi
    fi

    # Print message & reset text attributes
    if [[ -n ${3-} ]]; then
        printf '%s%b' "$1" "$ta_none"
    else
        printf '%s%b\n' "$1" "$ta_none"
    fi
}

# DESC: Only pretty_print() the provided string if verbose mode is enabled
# ARGS: $@ (required): Passed through to pretty_print() function
# OUTS: None
function verbose_print() {
    if [[ -n ${verbose-} ]]; then
        pretty_print "$@"
    fi
}

# DESC: Usage help
# ARGS: None
# OUTS: None
function script_usage() {
    cat << EOF
Usage:
     -h|--help                  Displays this help
     -v|--verbose               Makes output more verbose
     -n|--dry-run               Do dry-run of session builder
    -nc|--no-colour             Disables colour output
EOF
}

# DESC: Parameter parser
# ARGS: $@ (optional): Arguments provided to the script
# OUTS: Variables indicating command-line parameters and options
function parse_params() {
    local param
    while [[ $# -gt 0 ]]; do
        param="$1"
        shift
        case $param in
            -h | --help)
                script_usage
                exit 0
                ;;
            -n  | --dry-run)
                dry_run=true
                ;;
            *)
                script_exit "Invalid parameter was provided: $param" 1
                ;;
        esac
    done
}

function get_abs_filename() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

function send_email() {
    if [ "$1" = "no_log" ]; then
sendmail "${email_recipients}" << EOF
To: ${email_recipients}
From: ${email_sender}
Subject: ERROR in NexusLIMS record builder

No log file was produced. Most likely the NexusLIMS file storage location
was not properly mounted. Please check the record builder status.
EOF
    else
sendmail "${email_recipients}" << EOF
To: ${email_recipients}
From: ${email_sender}
Subject: ERROR in NexusLIMS record builder

There was an error (or unusual output) in the record builder. Here is the
output of ${LOGPATH}.
To help you debug, the following "bad" strings were found in the output:

${found_strings}

$(cat "${LOGPATH}")
EOF
fi
}

# DESC: Main control flow
# ARGS: $@ (optional): Arguments provided to the script
# OUTS: None
function main() {
    trap script_trap_err ERR
    trap script_trap_exit EXIT

    script_init "$@"
    parse_params "$@"
    colour_init

    # echo "Sourcing ${script_dir}/.env"
    # shellcheck disable=SC1090
    source "${script_dir}/.env"
    year=$(date +%Y)
    month=$(date +%m)
    day=$(date +%d)
    # shellcheck disable=SC2154
    LOGPATH_rel="${nexusLIMS_path}/../logs/${year}/${month}/${day}/$(date +%Y%m%d-%H%M).log"
    # make sure path to log file directory exists
    # echo "LOGPATH_rel is ${LOGPATH_rel}"
    mkdir -p "$(dirname "${LOGPATH_rel}")"
    LOGPATH=$(get_abs_filename "${LOGPATH_rel}")
    # echo "LOGPATH is ${LOGPATH}"

    python_args=""
    if [[ -n ${dry_run-} ]]; then
        python_args+="-n -vv"
        # replace end of log filepath with dryrun indicator
        LOGPATH=${LOGPATH/%.log/_dryrun.log}
        touch "${LOGPATH}"
        echo "Running script as dry run, not performing any actions" | tee -a "${LOGPATH}"
    else
        python_args="-vv"
        touch "${LOGPATH}"
    fi

    # check/create lock file and exit if needed 
    LOCKFILE=$(get_abs_filename "${nexusLIMS_path}/../.builder.lock")
    echo "Writing log to ${LOGPATH}" | tee -a "${LOGPATH}"
    if [ -f "${LOCKFILE}" ] ; then
        WE_CREATED_LOCKFILE=false
        echo "Lock file at ${LOCKFILE} already existed, so not running anything" | tee -a "${LOGPATH}"
        echo "Existing lock file last modified at $(stat "${LOCKFILE}" | grep Modify | cut -d ' ' -f2-)" | tee -a "${LOGPATH}"
    else
        WE_CREATED_LOCKFILE=true
        echo "Creating LOCKFILE at ${LOCKFILE}" | tee -a "${LOGPATH}"
        touch "${LOCKFILE}"

        # actually run record builder
        echo "Python args is ${python_args}" | tee -a "${LOGPATH}"
        abs_script_dir=$(get_abs_filename "${script_dir}")
        # echo "Abs script dir is ${abs_script_dir}"
        cd "${abs_script_dir}"
        poetry run python -m nexusLIMS.builder.record_builder ${python_args}  2>&1 | tee -a "${LOGPATH}"
    fi
}

main "$@"
