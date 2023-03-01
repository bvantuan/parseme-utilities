#!/bin/bash

echo "Next release for PARSEME Shared Task"

: <<'COMMENT'
# Set variables
DATA_DIR="/path/to/data"
RELEASE_VERSION="1.4"
RELEASE_NOTES="Initial release"

# Create release directory
RELEASE_DIR="$DATA_DIR/$RELEASE_VERSION"
mkdir "$RELEASE_DIR"

# Copy data files to release directory
cp -r "$DATA_DIR" "$RELEASE_DIR"

# Create release notes file
RELEASE_NOTES_FILE="$RELEASE_DIR/release_notes.txt"
echo "$RELEASE_NOTES" > "$RELEASE_NOTES_FILE"

# Commit and tag the release
cd "$DATA_DIR"
git add "$RELEASE_VERSION"
git commit -m "Release $RELEASE_VERSION"
git tag "$RELEASE_VERSION"

# Push the release to GitLab
git push origin master --tags
COMMENT