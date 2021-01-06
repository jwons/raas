library(provParseR)

setwd("/home/rstudio/datasets")

# Collects packages used in this environment
packages.df <- as.data.frame(installed.packages(), stringsAsFactors = F)[, c("Package", "Version")]
packages <- list()
for (row in 1:nrow(packages.df)){
  packages[[row]] <- c(packages.df[row,]$Package, packages.df[row,]$Version)
}

# Records version of R used 
lang.version <- paste(c(R.Version()$major, R.Version()$minor), collapse = ".")

# Collect container wide-info into one object
container.information <- list("Language Packages"=as.list(packages), "Language Version"=lang.version, "Language" = "R")

# Begin collecting script-level information. Need to identify all prov.json files
prov.jsons <- list.files(".", pattern="prov.json", recursive=T, full.names=FALSE)

# This code gathers the information from each individual script, collecting input files, output files, and warnings 
# for each script that has provenance. ind.scripts becomes a named list where the key is a full script path
# and the value is the data collected. 
ind.scripts <- list()
for (prov.json in prov.jsons){
  # The parser is initialized by creating a prov object that is passed to the various parsing functions
  prov.obj <- provParseR::prov.parse(prov.json)
  
  # Filename is used as key to the list
  filename <- provParseR::get.environment(prov.obj)[provParseR::get.environment(prov.obj)$label == "script",]$value
  
  # Gather data 
  input.files <- provParseR::get.input.files(prov.obj)$name
  output.files <- provParseR::get.output.files(prov.obj)$name
  data.nodes <- provParseR::get.data.nodes(prov.obj)
  warnings <- data.nodes[data.nodes$name == 'warning.msg',]$value
  
  # Condense and add to the final list
  script.info <- list("Input Files"= input.files, "Output Files"=output.files, "Warnings"=warnings)
  ind.scripts[[filename]] <- script.info
}

# Creat a single R object and then convert to json before writing to system to be read by RaaS
report <- list("Container Information"=container.information, "Individual Scripts"=ind.scripts)
report <- jsonlite::toJSON(report)
write(report, "/home/rstudio/report.json")