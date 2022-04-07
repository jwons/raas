doi_direct="$1"
static_analysis_dir="$2"

# suppress R output by redirecting to /dev/null
echo "Attempting to run static analysis for raw R scripts in dataset..."
Rscript --default-packages=methods,datasets,utils,grDevices,graphics,stats \
	app/language_r/static_analysis.R "$doi_direct" $static_analysis_dir