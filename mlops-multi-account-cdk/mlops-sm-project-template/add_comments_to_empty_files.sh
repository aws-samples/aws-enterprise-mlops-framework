#!/bin/bash

# Find all empty files in the current directory
empty_files=$(find . -type f -empty)

# Add comment to each empty file
echo $empty_files
for file in $empty_files; do
    echo "# Adding a comment here - empty files create issues with zipping https://github.com/aws/aws-cdk/issues/19012" >> "$file"
done

echo "Comments added to empty files."