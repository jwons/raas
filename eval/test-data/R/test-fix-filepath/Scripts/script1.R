print("Loading data originally hosted on a different computer")

foo <- read.csv("/home/users/Sequoyah/analyses/thesis/data/data.csv")

print(foo)

write.csv(foo, file = "/Results/result.csv")