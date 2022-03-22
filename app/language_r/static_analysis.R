##################################################
# Performs static analysis for each file, to collect
# required packages, system dependencies, warnings, 
# errors
# Command line arguments:
# dir_path_doi : string 
#				 path to the directory for which to run this script
# 
##################################################

library(CodeDepends)
library(lintr)
library(rjson)
library(Rclean)

# get commandline arguments
args = commandArgs(trailingOnly=TRUE)
# parse command line args for path to the directory
dir_path_doi = args[1] # example: "doi--10.7910-DVN-26905"  
static.analysis.dir = args[2] # Location of static analysis directory

print(dir_path_doi)

# set the working directory to the dataset directory
setwd(dir_path_doi)

print("Creating directory!\n")
# create directory to store provenance data
dir.create(static.analysis.dir, showWarnings = FALSE)


r_files <- list.files(".", pattern="\\.[Rr]\\>", recursive=T, full.names=T)
# parse out preprocessed files
preproc_files = grep("__preproc__", r_files)
if (length(preproc_files) > 0) {
	r_files <- r_files[-preproc_files]
}

# This function takes some text from a script and if the 
# text contains a install.packages function call where
# a variable is passed to the function rather than a 
# character literal, it returns the name of said variable.
# Otherwise returns NA
check.for.install.by.var <- function(script.text){
  parsed <- parse(text = script.text)
  
  # Begin to look through parse tree, recur inside as needed 
  pos.var <- check.expressions(parsed)
  if(pos.var != ""){
    return(pos.var[[1]])
  } else {
    return(NA)
  }
}

# This function, called recursively examines the parse tree of some code
# checking for install.packages function call where
# a variable is passed to the function. Either returns the variable name, 
# "" if nothing found, or recurs. 
check.expressions <- function(expr){
  if(length(expr) == 1 && typeof(expr) != "expression"){
    return("")
  } else if(length(expr[[1]]) == 1 && expr[[1]] == "install.packages"){
    if(typeof(expr[[2]]) == "symbol"){
      return(expr[[2]])
    } else {
      return("")
    }
    
  } else {
    ret.val <- unique(sapply(expr, check.expressions))
    ret.val <- ret.val[! ret.val %in% c('')]
    if(length(ret.val) > 0){
      return(ret.val)
    } else{
      return("")
    }
  }
}

# Given a file, this scripts will find the values of any variable used
# when passing a variable to an install.packages function.
# For example:
#
# list.of.packages <- c("rdtLite", "rdt", "ggplot2")
# install.packages(list.of.packages)
# 
# for the above script will return a character vector:
# ["rdtLite", "rdt", "ggplot2"]
get.variable.loaded.libs <- function(file){
  #lines <- readLines(file)
  #lines <- lines[unname(sapply(lines, grepl, pattern = "install.packages", fixed = T))]
  install.lines = paste(readLines(file), collapse = "\n")
  vars <- as.character(check.for.install.by.var(install.lines))
  if(is.na(vars)){
    pos.libs <- character()
  } else {
    code <- Rclean::clean(file, vars)
    parsed <- sapply(code, str2expression)
    script_env <- new.env()
    evals <- sapply(parsed, eval, envir=script_env)
    pos.libs <- c()
    for (var in evals){
      if(typeof(var) == "character"){
        pos.libs <- c(var, pos.libs)
      }
    }
    pos.libs <- unique(pos.libs)
  }
  
  return(pos.libs)
}

lint_file <- function(file) {
  
  # use only necessary linters
  select_linters <- list(absolute_path_linter = lintr::absolute_path_linter(lax=FALSE), 
                                nonportable_path_linter = lintr::nonportable_path_linter(lax=FALSE))
  
  # lint file, collect errors, collect other warnings
  res = lintr::lint(file, select_linters)

  errors_x <- character()
  warnings_x <- character()

  # collect errors and warnings
  for (r in res) {
    if (r$type == "warning") {
      warning <- paste(r$line, "Line:", r$line_number, r$message)
      warnings_x <- c(warnings_x, warning)
    }
    if (r$type == "error") {
      error <- paste(r$line, "Line:", r$line_number, r$message)
      errors_x <- c(errors_x, error)
    }
  }

  return(list(errors = errors_x, warnings = warnings_x))
}

get_library_inputs <- function(inputs) {
  res <- getInputs(inputs)
  libraries_used <- c()

  if (length(res) == 1) {
    if (length(res@libraries) != 0) {
      libraries_used <- c(libraries_used, res@libraries)
    }
  }

  else {
    lapply(res, function(r) {
     if (length(r@libraries) != 0) {
       libraries_used <- c(libraries_used, r@libraries)
     }
   })
  }

  return(libraries_used)
}

find_calls <- function(x) {
  if (is.atomic(x)) {
    return()
  } else if (is.name(x)) {
    return()
  } else if (is.call(x) || is.pairlist(x)) {
    # if getInputs finds a package, add it to the list and continue search
    if (!is.null(get_library_inputs(x))) {
      unique(c(get_library_inputs(x), unlist(lapply(x, find_calls))))
    }
    else {
      # continue search
      unique(unlist(lapply(x, find_calls)))
    }
  } else {
    stop("Don't know how to handle type ", typeof(x), 
      call. = FALSE)
  }
}

identify_packages <- function(file) {
  # error check here
  doc <- readScript(file)
  result <- getInputs(doc)

  packages_used <- c()

  for (r in result) {

    # get libraries found at top level
    if (length(r@libraries) != 0) {
      packages_used <- unique(c(packages_used, r@libraries))
    }

    # if libraries are not on top level CodeDepends will not pick 
    # them up as libraries on the first go
    # check in functions for "library" or "::" or "namespace" or "require"
    if (length(r@functions) != 0) {
      if ("library" %in% names(r@functions) || "::" %in% names(r@functions)
        || "namespace" %in% names(r@functions)|| "require" %in% names(r@functions)) {

        pack <- find_calls(r@code)
        packages_used <- unique(c(packages_used, pack))
      }
    }
  }
  
  # Libraries might be loaded through a variable rather than a character literal,
  # find those libraries here
  packages_used <- unique(c(packages_used, get.variable.loaded.libs(file)))
  
  return(packages_used)
}

libs <- character()
warnings <- character()
errors <- character()

print("Starting script linting")

# save packages and lints from each .R file
for (r_file in r_files) {
  # Collect libraries
  libs <- tryCatch(expr = {
    unique(c(identify_packages(r_file), libs, 'rdtLite'))
  }, error = function(cond){
    print(c(r_file, "Failed on Library"))
    libs
  })
  
  # Lint Files
  lints <- tryCatch(expr = {
    lint_file(r_file) 
  }, error = function(cond){
    print(c(r_file, "Failed on Lint"))
    NA
  })
  
  # only collect lints if no errors
  if(!is.na(lints[1])){
    new_warnings <- lints$warnings
    new_errors <- lints$errors
    
    warnings <- append(warnings, new_warnings)
    errors <- c(errors, new_errors)
  }
  
}

# get package dependencies
all.libs <- unique(unlist(sapply(libs, function(lib){
  tools::package_dependencies(lib, recursive = T)
})))

all.libs <- unique(c(libs, all.libs))

libs.request <- paste(all.libs, collapse=",")

# get system dependencies
print("Getting system reqs:")
print(paste("https://sysreqs.r-hub.io/pkg/", libs.request,"/linux-x86_64-ubuntu-gcc", sep = ""))

r <- httr::GET(paste("https://sysreqs.r-hub.io/pkg//linux-x86_64-ubuntu-gcc", sep = ""))
if(r$status == 404){
  api.resp = list()
} else {
  api.resp <- httr::content(r, as="parsed")
  api.resp <- unique(api.resp[api.resp != "NULL"])
}

response <- list( errors = if (length(errors) == 1) list(errors) else errors, 
                 warnings = if (length(warnings) == 1) list(warnings) else warnings, 
                 packages = unique(c(libs,all.libs)), 
                 package_deps = all.libs, 
                 sys_deps = api.resp)


json <- rjson::toJSON(response)
print(json)
write(json, paste(static.analysis.dir, "/static_analysis.json", sep=""))
