import sys
import pandas as pd
from preproc_helpers import all_preproc

# get the directory name as command line argument
doi_direct = sys.argv[len(sys.argv) - 1]

# read in the run log
run_log = pd.read_csv(doi_direct + "/prov_data/run_log.csv")
# for each file that ran
for _, my_row in run_log.iterrows():
	all_preproc(my_row["filename"], doi_direct, my_row["error"])