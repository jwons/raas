library(dplyr)

results = read.csv("results.csv", stringsAsFactors = F, header = F)
colnames(results) <- c("package", "num_of_containers")

potential.num <- unique(results$num_of_containers)
summary <- c()
for (num in potential.num){
  summary[num] <- length(results[results$num_of_containers == num,]$num_of_containers)
}

plot(summary, type = 'h')
