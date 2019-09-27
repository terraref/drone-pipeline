#!/bin/bash

#set -ev

# Get our current branch name and check that it's valid
CUR_BRANCH=$1
if [[ -z "${CUR_BRANCH}" ]]; then
    echo "Mising branch name parameter. Unable to continue."
    echo "usage: $0 <branch name> <alternate branch name> [starting folder]"
    exit 1
fi

# Special names that we need to change to match our job
LOWER_BRANCH_NAME=`echo "${CUR_BRANCH}" | tr '[:upper:]' '[:lower:]'`
if [[ "${LOWER_BRANCH_NAME}" = 'master' ]]; then
    NEW_BRANCH=$2
    if [[ -z "${NEW_BRANCH}" ]]; then
        echo "Invalid alternate branch name specified for ${CUR_BRANCH}. Unable to continue"
        exit 2
    fi
    CUR_BRANCH="${NEW_BRANCH}"
elif [[ "${LOWER_BRANCH_NAME}" = 'develop' ]]; then
    NEW_BRANCH=$2
    if [[ -z "${NEW_BRANCH}" ]]; then
        echo "Invalid alternate branch name specified for ${CUR_BRANCH}. Unable to continue"
        exit 2
    fi
    CUR_BRANCH="${NEW_BRANCH}"
elif [[ "${LOWER_BRANCH_NAME}" = *'travis'* ]]; then
    NEW_BRANCH=$2
    if [[ -z "${NEW_BRANCH}" ]]; then
        echo "Invalid alternate branch name specified for ${CUR_BRANCH}. Unable to continue"
        exit 2
    fi
    CUR_BRANCH="${NEW_BRANCH}"
fi

# Check if we need to change to another folder
NEW_FOLDER=$3
if [[ ! -z "${NEW_FOLDER}" ]]; then
    cd "${NEW_FOLDER}"
fi;

# Break the branch into parts so that we can search them
if [[ "${CUR_BRANCH}" = *"-"* ]]; then
    BRANCH_PARTS=$(echo "${CUR_BRANCH}" | tr "-" "\n")
elif [[ "${CUR_BRANCH}" = *"_"* ]]; then
    BRANCH_PARTS=$(echo "${CUR_BRANCH}" | tr "_" "\n")
elif [[ "${CUR_BRANCH}" = *" "* ]]; then
    BRANCH_PARTS=$(echo "${CUR_BRANCH}" | tr " " "\n")
else
    BRANCH_PARTS=("${CUR_BRANCH}")
fi

# Also prepare a backup in case the main match fails
NEW_BRANCH=$2
if [[ ! -z "${NEW_BRANCH}" ]]; then
    if [[ "${NEW_BRANCH}" = *"-"* ]]; then
        NEW_BRANCH_PARTS=$(echo "${NEW_BRANCH}" | tr "-" "\n")
    elif [[ "${NEW_BRANCH}" = *"_"* ]]; then
        NEW_BRANCH_PARTS=$(echo "${NEW_BRANCH}" | tr "_" "\n")
    elif [[ "${NEW_BRANCH}" = *" "* ]]; then
        NEW_BRANCH_PARTS=$(echo "${NEW_BRANCH}" | tr " " "\n")
    else
        NEW_BRANCH_PARTS=("${NEW_BRANCH}")
    fi
fi

# Loop through the folders looking for a match. Return when the main match
# works
for FOLDER in * ;
    do if [ -d "${FOLDER}" ]; then
        for B in $BRANCH_PARTS
        do
            if [[ "${FOLDER}" = *"${B}"* ]]; then
                if [[ ! -z "${NEW_FOLDER}" ]]; then
                    echo "${NEW_FOLDER}/${FOLDER}"
                else
                    echo "${FOLDER}"
                fi
                exit 0
            fi
        done;
        for N in $NEW_BRANCH_PARTS
        do
            if [[ "${FOLDER}" = *"${N}"* ]]; then
                if [[ ! -z "${NEW_FOLDER}" ]]; then
                    ALTERNATE_FOLDER="${NEW_FOLDER}/${FOLDER}"
                else
                    ALTERNATE_FOLDER="${FOLDER}"
                fi
            fi
        done;
    fi;
done

# IF we are here we couldn't find a match for the main folder.
if [[ ! -z "${ALTERNATE_FOLDER}" ]]; then
    echo "${ALTERNATE_FOLDER}"
    exit 0
fi

# We were not able to find anything
if [[ -z "${NEW_FOLDER}" ]]; then
    echo "Unable to find a match for branch ${CUR_BRANCH}"
else
    echo "Unable to find a match for branch ${CUR_BRANCH} in folder ${NEW_FOLDER}"
fi
exit 2
