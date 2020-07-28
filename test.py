import unittest
from data_dir import *
from DockerFileCreater import DockerFileCreater
from Parser import Parser
from ReportGenerator import ReportGenerator


# class test_for_generating_report(unittest.TestCase):
#     def test_something(self):
#         p=Parser("simulation.py","data1.dat data2.dat")
#         r = ReportGenerator()
#         self.assertEqual(r.generate_report(p), 0)

class test_for_dockerfile(unittest.TestCase):
    def test_zip_indataset(self):



if __name__ == '__main__':
    unittest.main()
