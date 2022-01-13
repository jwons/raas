import os
import docker
import json

from requests.exceptions import ConnectionError
from shutil import copy

from app.headless_raas import headless_raas

client = docker.from_env()
TEST_USER = "jwonsil/jwons-"


class TestFailure(Exception):
    pass


# This test checks if R preprocessing can correctly identify potentially missing files, when the check for failed
# scripts method is executed, there should be one script that failed.
def test_missing_files():
    print("======== R: Testing Missing File Detection ========")
    script_name = "test-missing-files.zip"
    copy(script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name)
    failed_scripts = check_for_failed_scripts(container_tag)
    if len(failed_scripts) != 1:
        result = False
        print("There should be one failed script")
    correct_files = verify_file_contents(container_tag,
                                         "home/rstudio/test-missing-files/missing_files.csv",
                                         '''"Script Name","Missing File"
"Scripts/script1.R","../Data/data.csv"
"Source/source1.R","../Source/source2.R"
''')
    if not correct_files:
        print("Missing Files not correctly identified")
        result = False
    client.containers.prune()
    client.images.remove(container_tag)
    os.remove("../datasets/" + script_name)
    if result is False:
        raise TestFailure("Test missing files failed")


# This test checks if the preprocessing feature for the R language can correctly inline sourced scripts,
# even recursively. There should be no failed scripts.
def test_recursive_source_call():
    print("======== R: Testing Source Call Inlining  ========")
    script_name = "test-recursive-source-call.zip"
    copy(script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name)
    failed_scripts = check_for_failed_scripts(container_tag)
    if len(failed_scripts > 0):
        result = False
    client.containers.prune()
    client.images.remove(container_tag)
    os.remove("../datasets/" + script_name)
    if result is False:
        raise TestFailure("Test source call inlining failed")


def verify_file_contents(container_tag, filepath, expected_contents):
    container = client.containers.run(image=container_tag, environment=["PASSWORD=pass"], detach=True)
    real_contents = container.exec_run("cat " + filepath)[1].decode()
    container.kill()
    ret_val = True
    if real_contents != expected_contents:
        ret_val = False
    return ret_val


def check_for_failed_scripts(name):
    failed_scripts = {}
    container = client.containers.run(image=name, environment=["PASSWORD=pass"], detach=True)
    report = json.loads(container.exec_run("cat /home/rstudio/report.json")[1].decode())
    ind_scripts = report["Individual Scripts"]
    for script, data in ind_scripts.items():
        if len(data["Errors"]) > 0:
            failed_scripts[script] = data["Errors"]
            print("Script: " + script + " failed with error: " + data["Errors"][0])
    container.kill()
    return failed_scripts


def invoke_raas(zip_name):
    result = headless_raas(name=os.path.splitext(zip_name)[0], lang="R", preproc="1",
                           zip_path=zip_name)
    return result


def execute_test(test_function):
    result = True
    try:
        test_function()
    except ConnectionError as conn_error:
        print("RaaS is likely not running")
        print(conn_error)
    except TestFailure as e:
        print(e)
        result = False
    except Exception as e:
        print("UNEXPECTED ERROR IN TESTS")
        print("Potential manual cleanup necessary")
        print(e)
        exit(1)
    print("")
    return result


if __name__ == "__main__":
    failed_tests = 0
    total_tests = 0
    tests = [test_missing_files,
             test_recursive_source_call]

    for test in tests:
        if not execute_test(test):
            failed_tests += 1
        total_tests += 1

    client.images.prune()

    print("Total Tests: " + str(total_tests))
    print("Tests Failed: " + str(failed_tests))
