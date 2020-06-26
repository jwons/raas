#!/bin/bash
doi_direct="$1"
r_collect="$2"

# suppress R output by redirecting to /dev/null
echo "Attempting to run and generate data provenance for raw python scripts in dataset..."
python3 $r_collect $doi_direct
