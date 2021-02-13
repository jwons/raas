import os
import shutil

from headless_raas import headless_raas

# Get all dataset dirs, remove first element because walk will return the datasets directory itself
# as the first element 
#dataset_dirs = [direc[0] for direc in os.walk("./eval/datasets")][1:]
def batch_raas(dataset_dirs, zip_dirs = False, debug = True):
	failed_set = []
	for data_dir in dataset_dirs[0:9]:
		# This code only needs to be run once
		if(zip_dirs):
			if(debug): print("Zipping: " + data_dir)
			shutil.make_archive("../raas_data/datasets/" + os.path.basename(data_dir), 'zip', data_dir)
		if(debug): print("Beginning containerization for: " + os.path.basename(data_dir))
		try:
			result = headless_raas(name = os.path.basename(data_dir), lang = "R", preproc = "1", zip_path = "datasets/" + os.path.basename(data_dir) + ".zip")
			if(result is False):
				print("raas function returned false")
				raise Exception("raas function returned false")
		except Exception as e:
			print("Containerization failed on: " + data_dir)
			print(e)
			failed_sets.append(data_dir)
	print("Reached end of list")
	return((0, failed_sets))	
