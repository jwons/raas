args = commandArgs(trailingOnly=TRUE)

dir_path_doi = args[1] # example: "doi--10.7910-DVN-26905"
preproc <- F
prov.dir <- "/home/rstudio/prov_data/"
print(dir_path_doi)

# set the working directory to the dataset directory
setwd(dir_path_doi)

print("Creating directory!\n")
# create directory to store provenance data
dir.create(prov.dir, showWarnings = FALSE)

# initialize dataframe to store results of attempting to run 
# (and collect provenance on) the script
run_log = data.frame(filename = c("bar"), 
					 error = c("fizz"), stringsAsFactors = FALSE)
run_log = run_log[-1,]
# initialize the csv with proper column names
write.csv(run_log, file=file.path(prov.dir, "run_log.csv"), row.names=FALSE)

# get correct list of r files to run the script on depending on commandline args
if (preproc) {
	r_files = list.files(".", pattern="__preproc__\\.[Rr]\\>", recursive=FALSE, full.names=FALSE)
} else {
	r_files = list.files(".", pattern="\\.[Rr]\\>", recursive=T, full.names=T)
	# parse out preprocessed files
	preproc_files = grep("__preproc__", r_files)
	if (length(preproc_files) > 0) {
		r_files = r_files[-preproc_files]
	}
}

sourced.scripts <- NA

# for each R file
for (r_file in r_files) {
  # If this is a sourced script do not run it independently, instead go to next file
  if(!is.na(sourced.scripts)){
    if(substr(r_file, 2, nchar(r_file)) %in% sourced.scripts){
      next
    }
  }
  
	# parse out file name, leaving out the ".R" part
	filename = substr(r_file, 1, nchar(r_file) - 2)
	# save local variables in case the script clears the workspace
	save(dir_path_doi, r_files, r_file, filename,
		 file=file.path(prov.dir, "get_prov.RData"))
	#setwd(script_dir)
	run.script <- paste0("R -e \"setwd('", paste0(dir_path_doi, substr(dirname(filename), 2, nchar(filename))), "'); error <-  try(source('", basename(r_file), "'", 
	                     "), silent = TRUE); if(class(error) == 'try-error'){save(error,file ='", file.path(prov.dir, "error.RData") ,"')}", "\"")
	result = tryCatch({
	  system(run.script, timeout = 3600)
	}, warning = function(w) {
	  w
	})

	timed.out <- F
	if(grepl("timed out after", result[[1]])){
	  timed.out <- T
	}
	
	# restore local variables
	load(file.path(prov.dir, "get_prov.RData"))

	# if there was an error
	if (file.exists(file.path(prov.dir, "error.RData"))) {
	  load(file.path(prov.dir, "error.RData"))
	  file.remove(file.path(prov.dir, "error.RData"))
		# trim whitespace from beginning and end of string
	  #error = str_trim(error[1])
	  # parse all the quotes from the error string
	  #error = str_replace_all(error, "\"", "")
	  # replace all newline characters in middle of string with special string
	  #error = str_replace_all(error, "[\n]", "[newline]")
	}
	else if (timed.out) {
	    error = "timed out"
	} else {
		error = "success"
		# copy the provenance
		#file.copy(paste0("prov_data/prov_",basename(filename) ,"/prov.json"), paste0("prov_data/", "prov_", basename(filename), ".json"))
	}
	# create dataframe from doi, filename, and errors to facilitate csv writing
	new_log_data = data.frame(filename=c(file.path(dir_path_doi, r_file)), error=c(gsub("[\r\n]", "", error)),
							  stringsAsFactors = FALSE)
	# write the new log data into the log file
	write.table(new_log_data, file=file.path(prov.dir, "run_log.csv"), sep=",", append=TRUE,
				row.names=FALSE, col.names=FALSE)
}

