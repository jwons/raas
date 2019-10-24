doi_direct="$1"

# suppress R output by redirecting to /dev/null
echo "Attempting to run and generate data provenance for raw R scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	app/get_dataset_provenance.R $doi_direct "n"