import re
import types

from pyaedt.generic.general_methods import GrpcApiError, _retry_ntimes, settings
import pyaedt.generic.grpc_plugin_dll as AedtAPI

logger = settings.logger
__all__ = ["CreateAedtApplication", "Release"]


def CreateAedtObj(objectID, bIsPropSvr, listFuncs):
    # print("Create " + str(objectID))
    if bIsPropSvr:
        return AedtPropServer(objectID, listFuncs)
    return AedtObjWrapper(objectID, listFuncs)


def CreateAedtBlockObj(list):
    count = len(list)
    if count > 1:
        if isinstance(list[0], str):
            toks = list[0].split(":")
            if len(toks) == 2:
                start = -1
                if count % 2 == 0:
                    if toks[1] == "=":
                        start = 2
                elif count > 2:
                    if toks[0] == "NAME":
                        start = 1
                if start > 0:
                    isBlock = True
                    for i in range(start, count - 1, 2):
                        if isinstance(list[i], str):
                            toks = list[i].split(":")
                            if len(toks) != 2 or toks[1] != "=":
                                isBlock = False
                                break
                        else:
                            isBlock = False
                            break
                    if isBlock:
                        return AedtBlockObj(list)
    return list


def GetAedtObjId(obj):
    if isinstance(obj, AedtObjWrapper):
        return obj.objectID
    return None


class AedtBlockObj(list):
    def GetName(self):
        if len(self) > 0:
            f = self[0]
            if isinstance(f, str):
                d = f.split(":")
                if len(d) == 2:
                    if d[0] == "NAME":
                        return d[1]

    def __GetValueIdxByKey__(self, keyName):
        for i in range(0, len(self) - 1):
            if isinstance(self[i], str):
                toks = self[i].split(":")
                if len(toks) == 2:
                    if toks[1] == "=" and toks[0] == keyName:
                        return i + 1
        raise GrpcApiError(keyName + " is not a key!")

    def __getitem__(self, idxOrKey):
        if isinstance(idxOrKey, str):
            idx = self.__GetValueIdxByKey__(idxOrKey)
            if idx != None:
                return super().__getitem__(idx)
        return super().__getitem__(idxOrKey)

    def __setitem__(self, idxOrKey, newVal):
        if isinstance(idxOrKey, int):
            if idxOrKey >= 0 or idxOrKey < len(self):
                oldItem = self.__getitem__(idxOrKey)
                if isinstance(oldItem, str):
                    toks = oldItem.split(":")
                    if len(toks) == 2 and (toks[1] == "=" or toks[0] == "NAME"):
                        raise GrpcApiError("The element is a key should not be overwritten!")
            return super().__setitem__(idxOrKey, newVal)
        if isinstance(idxOrKey, str):
            idx = self.__GetValueIdxByKey__(idxOrKey)
            if idx != None:
                return super().__setitem__(idx, newVal)
            raise GrpcApiError("Key not found")
        raise GrpcApiError("Must be key name or index")

    def keys(self):
        arr = []
        for i in range(0, len(self) - 1):
            if isinstance(self[i], str):
                toks = self[i].split(":")
                if len(toks) == 2 and toks[1] == "=":
                    arr.append(toks[0])
        return arr


class AedtObjWrapper:
    def __init__(self, objID, listFuncs):
        self.__dict__["objectID"] = objID  # avoid derive class overwrite __setattr__
        self.__dict__["__methodNames__"] = listFuncs
        # print(self.objectID)

    def __str__(self):
        return "Instance of an Aedt object:" + str(self.objectID)

    def __Invoke__(self, funcName, argv):
        if settings.enable_debug_grpc_api_logger:
            settings.logger.debug("{} {}".format(funcName, argv))
        try:
            return _retry_ntimes(
                settings.number_of_grpc_api_retries, AedtAPI.InvokeAedtObjMethod, self.objectID, funcName, argv
            )  # Call C function
        except:  # pragma: no cover
            raise GrpcApiError("Failed to execute grpc AEDT command: {}".format(funcName))

    def __dir__(self):
        return self.__methodNames__

    def __GetObjMethod__(self, funcName):
        try:

            def DynamicFunc(self, *args):
                return self.__Invoke__(funcName, args)

            return types.MethodType(DynamicFunc, self)
        except (AttributeError, GrpcApiError):
            raise GrpcApiError("This Aedt object has no attribute '" + funcName + "'")

    def __getattr__(self, funcName):
        try:
            if funcName == "ScopeID":  # backward compatible for IronPython wrapper.
                return self.objectID
            return self.__GetObjMethod__(funcName)
        except:
            raise GrpcApiError("Failed to get grpc API AEDT attribute {}".format(funcName))

    def __setattr__(self, attrName, val):
        if attrName == "objectID" or attrName == "__methodNames__":
            raise GrpcApiError("Modify this attribute is not allowed")
        elif attrName in self.__methodNames__:
            raise GrpcApiError(attrName + " is a function name")
        else:
            super().__setattr__(attrName, val)

    def __del__(self):
        AedtAPI.ReleaseAedtObject(self.objectID)

    def match(self, patternStr):  # IronPython wrapper implemented this function return IEnumerable<string>.
        class IEnumerable(list):
            def __getattr__(self, key):
                if key == "Count":
                    return len(self)

        pattern = re.compile(patternStr)
        found = IEnumerable()
        allMethods = self.__methodNames__
        for method in allMethods:
            if pattern.match(method):
                found.append(method)
        return found

    def GetHashCode(self):  # IronPython build in function
        return self.__hash__()


class AedtPropServer(AedtObjWrapper):
    def __init__(self, objID, listFuncs):
        AedtObjWrapper.__init__(self, objID, listFuncs)
        self.__dict__["__propMap__"] = None
        self.__dict__["__propNames__"] = None

    def __GetPropAttributes(self):
        if self.__propMap__ == None:
            propMap = {}
            propNames = self.GetPropNames()
            for prop in propNames:
                attrName = ""
                if prop[0].isdigit():
                    attrName += "_"
                for c in prop:
                    if c.isalnum() == True:
                        attrName += c
                    else:
                        attrName += "_"
                propMap[attrName] = prop
            self.__propMap__ = propMap
        return self.__propMap__

    def __dir__(self):
        ret = super().__dir__().copy()
        for attrName in self.__GetPropAttributes().keys():
            ret.append(attrName)
        return ret

    def __getattr__(self, attrName):
        try:
            return super().__getattr__(attrName)
        except AttributeError:
            # if AedtAPI.IsAedtObjPropName(self.objectID, attrName, False):
            #    return self.GetPropValue(attrName)
            propMap = self.__GetPropAttributes()
            if attrName in propMap:
                return self.GetPropValue(propMap[attrName])
            raise GrpcApiError("Failed to retrieve attribute {} from GRPC API".format(attrName))

    def __setattr__(self, attrName, val):
        if attrName in self.__dict__:
            self.__dict__[attrName] = val
            return

        # if AedtAPI.IsAedtObjPropName(self.objectID, attrName, True):
        #    self.SetPropValue(attrName, val)
        #    return
        propMap = self.__GetPropAttributes()
        if attrName in propMap:
            self.SetPropValue(propMap[attrName], val)
            return
        super().__setattr__(attrName, val)

    def GetName(self):
        return self.__Invoke__("GetName", ())

    def GetObjPath(self):
        return self.__Invoke__("GetObjPath", ())

    def GetChildNames(self, childType=""):
        return self.__Invoke__("GetChildNames", (childType))

    def GetPropNames(self, includeReadOnly=True):
        if includeReadOnly:
            if self.__propNames__ == None:
                self.__propNames__ = self.__Invoke__("GetPropNames", (includeReadOnly,))
            return self.__propNames__
        return self.__Invoke__("GetPropNames", (includeReadOnly,))

    def GetPropValue(self, propName=""):
        return self.__Invoke__("GetPropValue", (propName,))

    def SetPropValue(self, propName, val):
        return self.__Invoke__("SetPropValue", (propName, val))


def CreateAedtApplication(machine="", port=0, NGmode=False, alwaysNew=True):
    return AedtAPI.CreateAedtApplication(machine, port, NGmode, alwaysNew)


def Release():
    AedtAPI.ReleaseAll()


AedtAPI.SetPyObjCalbacks(CreateAedtObj, CreateAedtBlockObj, GetAedtObjId)
