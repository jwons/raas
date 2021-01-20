import sqlite3
import json
import docker

conn = sqlite3.connect('../app.db')

c = conn.cursor()

c.execute("SELECT dataset.report FROM dataset;")

def check_errors(report):
	no_errors = True
	num_errorless = 0
	num_errored = 0
	for script in report["Individual Scripts"]:
		print(script)
		if(len(report["Individual Scripts"][script]["Errors"]) > 0):
			no_errors = False
			print(report["Individual Scripts"][script]["Errors"])
			num_errored += 1
		else:
			num_errorless += 1
	return({"Errors": num_errored, "No Errors": num_errorless, "Container-Wide": no_errors})

error_results ={"Errors" : 0, "No Errors": 0, "Clean Containers": 0}
for row in c.execute("SELECT dataset.report FROM dataset;"):
	report = json.loads(row[0])
	print(report["Build Time"])
	print(report["Container Name"])
	set_results = check_errors(report)
	error_results["Errors"] += set_results["Errors"]
	error_results["No Errors"] += set_results["No Errors"]
	if(set_results["Container-Wide"]):
		error_results["Clean Containers"] += 1
print("Out of " + str(error_results["Errors"] + error_results["No Errors"]) + " total scripts")
print("Scripts without errors: " + str(error_results['No Errors']))
print("Scripts with errors: " + str(error_results['Errors']))
print("Number of clean containers " + str(error_results["Clean Containers"]))

