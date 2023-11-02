from ctypes import CFUNCTYPE, PyDLL, c_bool, c_int, c_wchar_p, py_object
import os

pathDir = os.environ["DesktopPluginPyAEDT"]  # DesktopPlugin
pathDir = os.path.dirname(pathDir)  # PythonFiles
pathDir = os.path.dirname(pathDir)  # DesktopPlugin or Win64
# dirName = os.path.basename(pathDir)


# Plugin filename depends on OS
if os.name != r"nt":
    pluginFileName = r"libPyDesktopPlugin.so"
else:
    pluginFileName = r"PyDesktopPlugin.dll"

AedtAPIDll_file = os.path.join(pathDir, pluginFileName)  # install dir

if not os.path.isfile(AedtAPIDll_file):
    pathDir = os.path.dirname(pathDir)  # lib
    pathDir = os.path.dirname(pathDir)  # core
    pathDir = os.path.dirname(pathDir)  # view
    AedtAPIDll_file = os.path.join(pathDir, r"build_output\64Release\PyDesktopPlugin.dll")  # develop dir
    # AedtAPIDll_file = os.path.join(pathDir, r"PyAedtStub/x64/Debug/PyAedtStub.dll") #develop dir

# load dll
if os.name == r"nt":
    # on windows, modify path
    aedtDir = os.path.dirname(AedtAPIDll_file)
    originalPath = os.environ["PATH"]
    os.environ["PATH"] = originalPath + os.pathsep + aedtDir
    AedtAPI = PyDLL(AedtAPIDll_file)
    os.environ["PATH"] = originalPath
else:
    AedtAPI = PyDLL(AedtAPIDll_file)

# AedtAPI.SetPyObjCalbacks.argtypes = py_object, py_object, py_object
AedtAPI.SetPyObjCalbacks.restype = None

# Must use global variable to hold those functions reference
callbackToCreateObj = None
callbackCreateBlock = None
callbackGetObjID = None


def SetPyObjCalbacks(CreateAedtObj, CreateAedtBlockObj, GetAedtObjId):
    callback_type = CFUNCTYPE(py_object, c_int, c_bool, py_object)
    global callbackToCreateObj
    global callbackCreateBlock
    global callbackGetObjID
    callbackToCreateObj = callback_type(CreateAedtObj)  # must use global variable to hold this function reference
    RetObj_InObj_Func_type = CFUNCTYPE(py_object, py_object)
    callbackCreateBlock = RetObj_InObj_Func_type(CreateAedtBlockObj)
    callbackGetObjID = RetObj_InObj_Func_type(GetAedtObjId)
    AedtAPI.SetPyObjCalbacks(callbackToCreateObj, callbackCreateBlock, callbackGetObjID)


# Find the version of AEDT from product info file
version = None
with open(os.path.join(pathDir, "product.info"), "r") as f:
    for line in f:
        if "AnsProductVersion" in line:
            version = line.split("=")[1].strip('\n"')
            break

if version >= "24.1":
    AedtAPI.CreateAedtApplication.argtypes = c_wchar_p, py_object, c_bool, c_bool
else:
    AedtAPI.CreateAedtApplication.argtypes = c_wchar_p, c_int, c_bool, c_bool

AedtAPI.CreateAedtApplication.restype = py_object

AedtAPI.InvokeAedtObjMethod.argtypes = c_int, c_wchar_p, py_object
AedtAPI.InvokeAedtObjMethod.restype = py_object

AedtAPI.ReleaseAedtObject.argtypes = (c_int,)
AedtAPI.ReleaseAedtObject.restype = None


def CreateAedtApplication(machine="", port=0, NGmode=False, alwaysNew=True):
    return AedtAPI.CreateAedtApplication(machine, port, NGmode, alwaysNew)


def InvokeAedtObjMethod(objectID, funcName, argv):
    return AedtAPI.InvokeAedtObjMethod(objectID, funcName, argv)


def ReleaseAedtObject(objectID):
    AedtAPI.ReleaseAedtObject(objectID)


def ReleaseAll():
    AedtAPI.ReleaseAll()


def IsEmbedded():
    return False
