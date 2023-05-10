print("Checking packages installed through variables can be loaded")

list.of.packages <- c("sp", "prettycode", "RCurl", "fuzzyjoin")

new.packages <- list.of.packages[!list.of.packages %in% installed.packages()]

if(length(new.packages)){
  install.packages(new.packages)
}

library(sp)
library(prettycode)
library(RCurl)
library(fuzzyjoin)