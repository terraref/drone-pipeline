#!/bin/bash
  
set -ev

TARGET_FILE=$1

# Check if there's a experiment.yaml file
if [[ ! -f "$TARGET_FILE" ]]; then
    # Not file, nothing to do
    echo "No file found to modify: $TARGET_FILE"
    exit 0
fi

SPACE_ID=$2
USER_NAME=$3
PASSWORD=$4

echo "Updating $TARGET_FILE"

# Remove all the lines related to clowder from the file
sed -i '/clowder/d' $TARGET_FILE
sed -i '/space/d' $TARGET_FILE
sed -i '/username/d' $TARGET_FILE
sed -i '/password/d' $TARGET_FILE

# Add them back in
echo "    clowder:" >> "$TARGET_FILE"
echo "        space: $SPACE_ID" >> "$TARGET_FILE"
echo "        username: $USER_NAME" >> "$TARGET_FILE"
echo "        password: $PASSWORD" >> "$TARGET_FILE"
