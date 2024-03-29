import os
import docker
import json

from requests.exceptions import ConnectionError
from shutil import copy

from app.headless_raas import headless_raas

client = docker.from_env()
TEST_USER = "jwonsil/jwons-"
r_datadir = "R/"
py_datadir = "Python/"


class TestFailure(Exception):
    pass


# ============================
# ===== R Tests Functions ====
# ============================

# This test checks if R preprocessing can correctly identify potentially missing files, when the check for failed
# scripts method is executed, there should be one script that failed.
def test_missing_files():
    print_r_testname("Missing File Detection")
    script_name = "test-missing-files.zip"
    copy(r_datadir + script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name, 'R')
    failed_scripts = check_for_failed_r_scripts(container_tag)
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
    print_r_testname("Source Call Inlining")
    script_name = "test-recursive-source-call.zip"
    copy(r_datadir + script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name, "R")
    failed_scripts = check_for_failed_r_scripts(container_tag)
    if len(failed_scripts) > 0:
        result = False
    client.containers.prune()
    client.images.remove(container_tag)
    os.remove("../datasets/" + script_name)
    if result is False:
        raise TestFailure("Test source call inlining failed")


def test_fixing_filepath():
    print_r_testname("Fixing Filepaths")
    script_name = "test-fix-filepath.zip"
    copy(r_datadir + script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name, "R")
    failed_scripts = check_for_failed_r_scripts(container_tag)
    if len(failed_scripts) > 0:
        result = False
    client.containers.prune()
    client.images.remove(container_tag)
    os.remove("../datasets/" + script_name)
    if result is False:
        raise TestFailure("Test fixing filepath failed")


# ============================
# == Python Tests Functions ==
# ============================

def test_normal():
    print_py_testname("Normal Operation")
    script_name = "test-normal.zip"
    copy(py_datadir + script_name, "../datasets/")
    container_tag = TEST_USER + os.path.splitext(script_name)[0]
    result = invoke_raas(script_name, "Python")
    '''
    failed_scripts = check_for_failed_scripts(container_tag)
    if len(failed_scripts) > 0:
        result = False
    '''
    client.containers.prune()
    client.images.remove(container_tag)
    os.remove("../datasets/" + script_name)
    if result is False:
        raise TestFailure("Test python normal execution failed")


# ============================
# ===== Helper functions =====
# ============================

def print_r_testname(testname):
    print_lang_testname(testname, "R")


def print_py_testname(testname):
    print_lang_testname(testname, "Python")


def print_lang_testname(testname, lang):
    print("======== " + lang + ": " + testname + "  ========")


def verify_file_contents(container_tag, filepath, expected_contents):
    container = client.containers.run(image=container_tag, environment=["PASSWORD=pass"], detach=True)
    real_contents = container.exec_run("cat " + filepath)[1].decode()
    container.kill()
    ret_val = True
    if real_contents != expected_contents:
        ret_val = False
    return ret_val


def check_for_failed_r_scripts(name):
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


def invoke_raas(zip_name, language):
    result = headless_raas(name=os.path.splitext(zip_name)[0], lang=language, preproc="1",
                           zip_path=zip_name)
    return result


def execute_test(test_function):
    result = True
    try:
        test_function()
    except ConnectionError as conn_error:
        print("RaaS is likely not running")
        print(conn_error)
        exit(1)
    except TestFailure as e:
        print(e)
        result = False
    except Exception as e:
        print("UNEXPECTED ERROR IN TESTS")
        print(e)
        print("Potential manual cleanup of test data necessary")
        exit(1)
    print("")
    return result


if __name__ == "__main__":
    failed_tests = 0
    total_tests = 0

    r_tests = [
        test_missing_files,
        test_recursive_source_call,
        test_fixing_filepath
    ]

    py_tests = [
        test_normal
    ]

    #r_tests = []

    # Run R tests
    for test in r_tests:
        if not execute_test(test):
            failed_tests += 1
        total_tests += 1

    # Run Python tests
    for test in py_tests:
        if not execute_test(test):
            failed_tests += 1
        total_tests += 1

    client.images.prune()

    print("Total Tests: " + str(total_tests))
    print("Tests Failed: " + str(failed_tests))
