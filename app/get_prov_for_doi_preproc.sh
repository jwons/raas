doi_direct="$1"

# suppress R output by redirecting to /dev/null
echo "Attempting to generate data provenance for raw R scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	app/get_dataset_provenance.R $doi_direct "n" &> /dev/null

echo "Preprocessing code for the dataset..."
python app/preprocess_r_scripts.py $doi_direct

# suppress R output by redirecting to /dev/null
echo "Attempting to generate data provenance for pre-processed R scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	app/get_dataset_provenance.R $doi_direct "y" &> /dev/null