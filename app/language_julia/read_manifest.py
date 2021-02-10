def read_manifest(loc):	

	file = open(loc+'/'+'Manifest.toml')

	package_list = {}
	# package_vs = set()
	project = file.readlines()
	n = len(project)
	for i in range(n):
		project[i] = project[i].strip()

	# print(project)
	current_package = ""
	for line in project:
		if (line==""):
			continue
		if (line[0:2]=="[["):
			dep = line[2:-2]
			package_list[dep] = '"-1"'
			current_package = dep
		elif (line[:7]=="version"):
			if ('+' in line[11:]):
				line1 = line[11:].split('+')
				ver = line1[0]
				if (ver[0]!='"'):
					ver = '"'+ver
				package_list[current_package] = ver+'"'
			else:
				package_list[current_package] = '"'+line[11:-1]+'"'
		else:
			pass

	return (package_list)

# print(read_manifest('/home/prakhar/Provenance/raas/app/language_julia'))