def read_project(loc):

	file = open(loc+'/''Project.toml')

	package_list = {}
	# package_vs = set()
	project = file.readlines()
	n = len(project)
	for i in range(n):
		project[i] = project[i].strip()

	# print(project)
	flag = 0
	for line in project:
		if (line==""):
			continue
		if (line=="[deps]" or line=="[extras]"):
			flag = 1
		elif (line=="[compat]"):
			flag = 2
		elif (line[0]=="[" and line[-1]=="]"):
			flag = 0
		else:
			if (flag==1):
				line1 = line.split()
				if (line1[0] not in package_list):
					package_list[line1[0]] = '"-1"' # -1 stands for default version
			if (flag==2):
				line1 = line.split()
				ver = line1[-1]
				if (ver[0]!='"'):
					ver = '"'+ver
				package_list[line1[0]] = ver


	return (package_list)
# print (package_vs)
# print(read_project('/home/prakhar/Provenance/raas/app/language_julia'))