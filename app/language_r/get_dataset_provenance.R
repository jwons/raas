##################################################
# Attempts to collect provenance data for each file, logging errors if necessary
# Command line arguments:
# dir_path_doi : string 
#				 path to the directory for which to run this script
# preproc : string
# 			either "y" or "n"
##################################################

library(stringr)
library(rdtLite)
library(provParseR)

# get commandline arguments
args = commandArgs(trailingOnly=TRUE)
# parse command line args for path to the directory and preprocessing
dir_path_doi = args[1] # example: "doi--10.7910-DVN-26905"
prov.dir <- file.path(dir_path_doi, "/../prov_data")
run.log.file <- file.path(prov.dir, "/run_log.csv")
error.file <- file.path(prov.dir, "/error.RData")

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
write.csv(run_log, file=run.log.file, row.names=FALSE)

# get correct list of r files to run
r_files = list.files(".", pattern="\\.[Rr]\\>", recursive=T, full.names=T)
# parse out preprocessed files
preproc_files = grep("__preproc__", r_files)
if (length(preproc_files) > 0) {
	r_files = r_files[-preproc_files]
}


sourced.scripts <- NA

if(file.exists("../.srcignore")){
  sourced.scripts <- readLines(con = "../.srcignore")
}

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
		 file=paste(prov.dir, "/get_prov.RData", sep =""))
	#setwd(script_dir)
	run.script <- paste0("R -e \"library(rdtLite); setwd('", paste0(dir_path_doi, substr(dirname(filename), 2, nchar(filename))), "'); error <-  try(prov.run('", basename(r_file), "', prov.dir = '", prov.dir ,
	                     "'), silent = TRUE); if(class(error) == 'try-error'){save(error,file ='", paste0(prov.dir, "/error.RData") ,"')}", "\"")
	system(run.script)

	# Determine provenance directory so it can be changed to a unique name
	script.no.ext <- basename(filename)
	old.prov.dir <- paste0(prov.dir, "/", paste0("prov_", script.no.ext))
	script.no.ext <- basename(old.prov.dir)

	# Switch all periods and forward slashes to dashes and then remove first occurences
	# Will turn "./Scripts/anotherTest" into first "--Scripts-anotherTest" and then "Scripts-anotherTest"
	# Then append to the prov directory
	new.prov.dir <- str_replace_all(filename, "[\\/.]", "-")
	new.prov.dir <- str_replace_all(new.prov.dir, "^-*", "")
	new.prov.dir <- paste0(dirname(old.prov.dir), "/", new.prov.dir)

	# Execute renaming
	system(paste0("mv ", old.prov.dir, " ", new.prov.dir))

	# restore local variables
	load(paste0(prov.dir, "/get_prov.RData"))
	# if there was an error
	if (file.exists(error.file)) {
	  load(error.file)
	  file.remove(error.file)
		# trim whitespace from beginning and end of string
	  error = str_trim(error[1])
	  # parse all the quotes from the error string
	  error = str_replace_all(error, "\"", "")
	  # replace all newline characters in middle of string with special string
	  error = str_replace_all(error, "[\n]", "[newline]")
	} else {
		error = "success"
		# copy the provenance
		#file.copy(paste0("prov_data/prov_",basename(filename) ,"/prov.json"), paste0("prov_data/", "prov_", basename(filename), ".json"))
	}
	# create dataframe from doi, filename, and errors to facilitate csv writing
	new_log_data = data.frame(filename=c(r_file), error=c(error),
							  stringsAsFactors = FALSE)
	# write the new log data into the log file
	write.table(new_log_data, file=run.log.file, sep=",", append=TRUE,
				row.names=FALSE, col.names=FALSE)
}

missing.lists = list.files("../", pattern="missing_files.txt", recursive=TRUE, full.names=FALSE)
if(length(missing.lists) > 0){
	missing.files <- data.frame()

	for(missing.list in missing.lists){
	  missing.table <- read.csv(missing.list, header = F)
	  missing.table$V1 <- file.path(dirname(missing.list), missing.table$V1)
	  missing.files <- rbind(missing.files, missing.table)
	}
	colnames(missing.files) <- c("Script Name", "Missing File")
	write.csv(x = missing.files, file =  "../missing_files.csv", row.names = F)
}