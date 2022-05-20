library(provParseR)
library(stringr)

# get commandline arguments
args = commandArgs(trailingOnly=TRUE)
# parse command line args for path to the directory and preprocessing
prov.data.dir = args[1]

setwd("/home/rstudio")

# This function is used to create a list of rows from a dataframe to make it easier to jsonify
# It is used for system libraries and language packages
create.json.list <- function(lib.frame){
  libs <- list()
  for (row in 1:nrow(lib.frame)){
    libs[[row]] <- c(lib.frame[row,]$Package, lib.frame[row,]$Version)
  }
  return(libs)
}

# Go to system and query apt for installed packages, but will still need to parse output
system.libs <- system("apt list --installed", intern = T)
system.libs <- system.libs[2:length(system.libs)]

# Grab just the pacakge name [1] and then the version [2]
system.libs.max <- t(sapply(X = system.libs, FUN = function(x){
  str_split(string = x, pattern = " ")[[1]][1:2]
}))

# Clear out names, most aesthetic
rownames(system.libs.max) <- NULL
colnames(system.libs.max) <- c("Package", "Version")

# Create the list that will be placed into the report
system.libs.list <- create.json.list(as.data.frame(system.libs.max, stringsAsFactors = F))

# Collects packages used in this environment
packages.df <- as.data.frame(installed.packages(), stringsAsFactors = F)[, c("Package", "Version")]
packages <- create.json.list(packages.df)

# Records version of R used
lang.version <- paste(c(R.Version()$major, R.Version()$minor), collapse = ".")

# Collect container wide-info into one object
container.information <- list("Language Packages"=as.list(packages), "System Libraries" = system.libs.list, "Language Version"=lang.version, "Language" = "R")

# Begin collecting script-level information. Need to identify all prov.json files
prov.jsons <- list.files(prov.data.dir, pattern="prov.json", recursive=T, full.names=FALSE)

check.filename.in.runlog <- function(run.log.filename, prov.filename){
  run.split <- str_split(run.log.filename, "/")[[1]][-1]
  prov.split <- tail(str_split(prov.filename, "/")[[1]], length(run.split))
  eql.set <- unique(run.split == prov.split)
  return(T %in% eql.set && !F %in% eql.set)
}

# Contains information about whether a script timed out
run.log <- read.csv(file.path(prov.data.dir, "run_log.csv"))

# Master list of r scripts in a dataset
r.scripts <- basename(as.character(run.log$filename))

# This code gathers the information from each individual script, collecting input files, output files, and warnings
# for each script that has provenance. ind.scripts becomes a named list where the key is a full script path
# and the value is the data collected.
ind.scripts <- list()
for (prov.json in prov.jsons){
  # The parser is initialized by creating a prov object that is passed to the various parsing functions
  prov.obj <- provParseR::prov.parse(file.path(prov.data.dir, prov.json))

  # Filename is used as key to the list
  filename <- provParseR::get.environment(prov.obj)[provParseR::get.environment(prov.obj)$label == "script",]$value

  # Keep track of which files have been processed
  r.scripts <- r.scripts[r.scripts != basename(filename)]


  # Check for matching file in run log
  run.mask <- unlist(lapply(run.log[["filename"]], check.filename.in.runlog, prov.filename=filename))
  run.log.row <- run.log[run.mask, ]

  timed.out <- F
  if(nrow(run.log.row) == 1 && run.log.row[["error"]] == "timed out"){
    timed.out <- T
  }


  # Gather data
  input.files <- unique(provParseR::get.input.files(prov.obj)$name)
  output.files <- unique(provParseR::get.output.files(prov.obj)$name)
  data.nodes <- provParseR::get.data.nodes(prov.obj)
  warnings <- data.nodes[data.nodes$name == 'warning.msg',]$value
  errors <- data.nodes[data.nodes$name == 'error.msg',]$value
  # Condense and add to the final list
  script.info <- list("Input Files"= input.files, "Output Files"=output.files, "Warnings"=warnings, "Errors" = errors, "Timed Out"= as.character(timed.out))
  ind.scripts[[filename]] <- script.info
}

# If a script didn't have prov it will show up here
if(length(r.scripts) > 0){
  for (no.prov.script in r.scripts){
    script.info <- list("Input Files"= c(), "Output Files"=c(), "Warnings"=c(), "Errors" = c("rdtLite Error"), "Timed Out"= as.character(F))
    ind.scripts[[no.prov.script]] <- script.info
  }
}

# Creat a single R object and then convert to json before writing to system to be read by RaaS
report <- list("Container Information"=container.information, "Individual Scripts"=ind.scripts)
report <- jsonlite::toJSON(report)
write(report, "/home/rstudio/report.json")
