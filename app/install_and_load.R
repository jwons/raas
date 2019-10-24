##### INJECTED TO FACILITATE REPRODUCIBILITY ##################################
# helper function to load packages, installing them if necessary
if (!require("stringr", character.only=TRUE)){
      install.packages(pkgs="stringr", repos="http://cran.r-project.org")
      require("stringr", character.only=TRUE)
}
install_and_load <- function(x, ...){
  # if the input is a string
  if (is.character(x) & length(x) == 1) {
    # check if there are commas in the string
    if (grepl(",", x)) {
      # change x to a vector of strings if there are commas
      x = str_split(x, ",")[[1]]
    }
  }
  for (package in x) {
    if (!require(package, character.only=TRUE)){
      install.packages(pkgs=package, repos="http://cran.r-project.org")
      require(package, character.only=TRUE)
    }
  }
}
###############################################################################