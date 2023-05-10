r_collection_script="$1"
dataset_directory="$2"


echo "Attempting to run and generate data provenance for raw scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	$r_collection_script "$dataset_directory"
