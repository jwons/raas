doi_direct="$1"
r_collect="$2"

echo "Attempting to run and generate data provenance for raw scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	$r_collect $doi_direct
