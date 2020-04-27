import json
import re
import pandas as pd

class Parser:

    # holds the dictionary of provenance
    _provData = {}
    
    #Holds a dictionary of data frames where each data frame is an 
    # "element" of the provenance. e.g procedure nodes, data nodes, etc.
    _provElements = {}

    # Constructor takes a filepath to a provenance file and reads in 
    # the information into memory
    def __init__(self, inputProv, isFile = True):
        prov = ""
        
        # before the json can be converted into a Pythonic structure
        # it has to be 'cleaned.' prefixes and comments are removed
        provLines = []

        if(isFile):
            with open(inputProv) as provJson:
                provLines = provJson.readlines()
        else:
            provLines = inputProv.split("\n")

        for line in inputProv:
            if("//" in line):
                provLines.remove(line)

        prov = ''.join(provLines)
        prov = prov.replace("rdt:", "")
        prov = prov.replace("prov:", "")
        prov = json.loads(prov)

        

        # Unlist the nested dictionary by one level. This 
        # way we have a 'master list' of provenance nodes and edges
        for provKey in prov:
            for provElement in prov[provKey]:
                self._provData[provElement] = prov[provKey][provElement]

        # Here start building up the parsed dic that will be queried by getter functions
        provChars = {"procNodes":"p", "dataNodes":"d", "funcNodes":"f",
                    "procProcEdges":"pp", "procDataEdges":"pd", "dataProcEdges":"dp",
                    "funcProcEdges":"fp", "funcLibEdges":"m", "agents":"a"}

        for key in provChars:
            self._provElements[key] = self._parseGeneral(provChars[key])

        # Add the environment prov data
        d = dict((k, self._provData[k]) for k in ["environment"])
        self._provElements["environment"] = pd.DataFrame(data = d)

        # Add the libraries used 
        d = self._parseGeneral("l")
        self._provElements["libraries"] = d[["name", "version"]]

        # Add the scripts sourced 
        d = dict((k, self._provData["environment"][k]) for k in ["sourcedScripts", "sourcedScriptTimeStamps"])
        self._provElements["scripts"] = pd.DataFrame(data = d, index = range(0, len(d["sourcedScripts"])))

    # To process nodes/edges from the master list the same process can be used
    # for most of them. This function handles converting dicts to the necessary data frame.
    def _parseGeneral(self, requested):

        # regex matches when a string starts with the letter(s) requested and is followed
        # by a variable amount of digits, and the string ends after the digits
        regex = "^" + requested + "\\d+$"
        
        # finding all of the matching keys using regex
        matches = [string for string in self._provData.keys() if re.match(regex,string)]
        
        # make a dict that can be converted into a data frame from those keys
        d = dict((k, self._provData[k]) for k in matches)

        retVal = pd.DataFrame(data = d).T

        labels = list(retVal.index)

        retVal["label"] = pd.Series(labels, index = retVal.index)

        return(retVal)

    # Access function to get any part of the parsed provenance
    def getProvInfo(self, requestedProv):
        df = self._provElements[requestedProv]
        try:
            df = df.iloc[df.index.str.extract(r'(\d+)', expand=False).astype(int).argsort()]
        except ValueError:
            pass

        return(df)

    def getEnvironment(self):
        return(self.getProvInfo("environment"))

    def getLibs(self):
        return(self.getProvInfo("libraries"))

    def getScripts(self):
        return(self.getProvInfo("scripts"))

    def getProcNodes(self):
        return(self.getProvInfo("procNodes"))

    def getDataNodes(self):
        return(self.getProvInfo("dataNodes"))

    def getFuncNodes(self):
        return(self.getProvInfo("funcNodes"))

    def getProcProc(self):
        return(self.getProvInfo("procProcEdges"))

    def getDataProc(self):
        return(self.getProvInfo("dataProcEdges"))

    def getProcData(self):
        return(self.getProvInfo("procDataEdges"))

    def getFuncProc(self):
        return(self.getProvInfo("funcProcEdges"))

    def getFuncLib(self):
        return(self.getProvInfo("funcLibEdges"))


    # This function returns the files that were read in to the script.
    # It does this by checking the data nodes of the type "File",
    # with data to procedure edges. 
    def getInputFiles(self):
        dataNodes = self.getDataNodes()

        dataNodes = dataNodes[dataNodes.type.isin(["File"])]
        if(len(dataNodes.index) != 0):
            dataProc = list(self.getDataProc()["entity"])
            dataNodes = dataNodes[dataNodes.index.isin(dataProc)]

        return(dataNodes[["name", "location", "timestamp"]])
    
    # This function returns the files that were read in to the script.
    # It does this by checking the data nodes of the type "File",
    # with procedure to data edges. 
    def getOutputFiles(self):
        dataNodes = self.getDataNodes()

        dataNodes = dataNodes[dataNodes.type.isin(["File"])]
        if(len(dataNodes.index) != 0):
            procData = list(self.getProcData()["entity"])
            dataNodes = dataNodes[dataNodes.index.isin(procData)]

        return(dataNodes[["name", "location", "timestamp"]])
