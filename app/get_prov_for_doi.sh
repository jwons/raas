doi_direct="$1"
r_collect="$2"

# suppress R output by redirecting to /dev/null
echo "Attempting to run and generate data provenance for raw R scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	$r_collect $doi_direct "n"