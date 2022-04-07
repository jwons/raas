install.packages("R.utils")
R.utils::setOption("repos", c(CRAN = "https://cran.microsoft.com/snapshot/2022-03-18"))
install.packages("renv")
install.packages("rdtLite")

#devtools::install_github("End-to-end-provenance/provParseR")
#devtools::install_github("End-to-end-provenance/provViz")
#devtools::install_github("End-to-end-provenance/provSummarizeR")
#devtools::install_github("End-to-end-provenance/rdtLite")  

#library(renv)

list.of.packages = commandArgs(trailingOnly=TRUE)

list.of.packages <- list.of.packages[!list.of.packages %in% installed.packages()]

generate.mran.url <- function(date){
  gsub(" ", "", paste("https://cran.microsoft.com/snapshot/", date, collapse = ""))
}

og.repo <- unname(getOption("repos"))
standard.snapshots <- c(as.Date("2022-03-23"),
                        as.Date("2020-07-16"), # R Open 4.0.2
                        as.Date("2020-04-23"), # 3.6
                        as.Date("2019-04-15"), # 3.5
                        as.Date("2018-04-01"), # 3.4
                        as.Date("2017-03-15")) # 3.3
repos.to.try <- c(og.repo)
for(i in 1:length(standard.snapshots)){
  repos.to.try <- c(repos.to.try, generate.mran.url(format(standard.snapshots[i],"%Y-%m-%d")))
}

r.lib.path <- "/home/rstudio/r_packages"
dir.create(r.lib.path)

if(length(list.of.packages) == 0){
  success.install <- T
} else {
  for(repo.to.try in repos.to.try){
    R.utils::setOption("repos", c(CRAN = repo.to.try))

    success.install <- tryCatch({
      renv::use(library = r.lib.path)
      renv::install(list.of.packages)
      T
    }, error = function(e) {
      print(e)
      unlink(r.lib.path, recursive = T)
      dir.create(r.lib.path)
      return(F)
    })

    if(success.install){
      print(paste("Chosen snapshot is:", repo.to.try))
      break
    }
  }
}

if(success.install){
  r.environ.path <- "/home/rstudio/.Renviron"
  file.create(r.environ.path)
  r.lib.env <- paste0("R_LIBS=", r.lib.path)
  write(r.lib.env,file=r.environ.path,append=TRUE)
}



