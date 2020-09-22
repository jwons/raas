##################################################
# Attempts to collect provenance data for each file, logging errors if necessary
# Command line arguments:
# dir_path_doi : string 
#				 path to the directory for which to run this script
# preproc : string
# 			either "y" or "n"
##################################################

# get commandline arguments
args = commandArgs(trailingOnly=TRUE)
# parse command line args for path to the directory and preprocessing
dir_path_doi = args[1] # example: "doi--10.7910-DVN-26905"
preproc = args[2] == "y" # preprocessing


print(dir_path_doi)

# set the working directory to the dataset directory
setwd(dir_path_doi)
library(stringr)
library(rdtLite)
library(provParseR)

print("Creating directory!\n")
# create directory to store provenance data
dir.create("prov_data", showWarnings = FALSE)

# initialize dataframe to store results of attempting to run 
# (and collect provenance on) the script
run_log = data.frame(filename = c("bar"), 
					 error = c("fizz"), stringsAsFactors = FALSE)
run_log = run_log[-1,]
# initialize the csv with proper column names
write.csv(run_log, file="prov_data/run_log.csv", row.names=FALSE)

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
		 file="prov_data/get_prov.RData")
	#setwd(script_dir)
	run.script <- paste0("R -e \"library(rdtLite); setwd('", paste0(dir_path_doi, substr(dirname(filename), 2, nchar(filename))), "'); error <-  try(prov.run('", basename(r_file), "', prov.dir =  '", paste0(dir_path_doi, "/prov_data'") , 
	                     "), silent = TRUE); if(class(error) == 'try-error'){save(error,file ='", paste0(dir_path_doi, "/prov_data/error.RData") ,"')}", "\"")
	system(run.script)

	# restore local variables
	load("prov_data/get_prov.RData")
	# if there was an error
	if (file.exists("prov_data/error.RData")) {
	  load("prov_data/error.RData")
	  file.remove("prov_data/error.RData")
		# trim whitespace from beginning and end of string
	  error = str_trim(error[1])
	  # parse all the quotes from the error string
	  error = str_replace_all(error, "\"", "")
	  # replace all newline characters in middle of string with special string
	  error = str_replace_all(error, "[\n]", "[newline]")
	}
	else {
		error = "success"
		# copy the provenance
		#file.copy(paste0("prov_data/prov_",basename(filename) ,"/prov.json"), paste0("prov_data/", "prov_", basename(filename), ".json"))
	}
	# create dataframe from doi, filename, and errors to facilitate csv writing
	new_log_data = data.frame(filename=c(r_file), error=c(error),
							  stringsAsFactors = FALSE)
	# write the new log data into the log file
	write.table(new_log_data, file="prov_data/run_log.csv", sep=",", append=TRUE,
				row.names=FALSE, col.names=FALSE)
}

# We will also need the system requirements from these packages to install in 
# in the container. This is accomplished by finding all packages (recursively)
# this analysis uses, and then queries a sysreqs database API to find system requirements

# Libraries called in analysis
prov.dirs <- list.dirs("prov_data", recursive = F)
libs <- c()
sourced.scripts <- c()
for (prov.dir in prov.dirs){
  parsed.prov <- provParseR::prov.parse(prov.input = paste0(prov.dir,"/prov.json"), isFile = T)
  libs <- append(libs, provParseR::get.libs(parsed.prov)$name)
  sourced <- as.vector(provParseR::get.scripts(parsed.prov)[-1,]$script)
  sourced.scripts <- append(sourced.scripts, as.vector(sapply(X = sourced, FUN = function(script){sub(dir_path_doi, "", script)})))
}

#parsed.prov <- provParseR::prov.parse(prov.input = prov.json(), isFile = F)
#libs <- provParseR::get.libs(parsed.prov)

# All libraries including implicit
all.libs <- unique(unlist(append(libs, sapply(libs, function(lib){
  tools::package_dependencies(lib, recursive = T)
}))))

# Make API call
libs.request <- paste(all.libs, collapse=",")
api.resp <- httr::content(httr::GET(paste("https://sysreqs.r-hub.io/pkg/", libs.request,"/linux-x86_64-ubuntu-gcc", sep = "")), as="parsed")
api.resp <- unique(api.resp[api.resp != "NULL"])
sys.deps <- paste(api.resp, collapse = " ")

# Save sysreqs info 
write(sys.deps, paste0("prov_data/", "sysreqs.txt"))

# don't repeat scripts
sourced.scripts <- unique(sourced.scripts)

# Save Sourced Scripts
write(unlist(sourced.scripts), "prov_data/sourced.txt")