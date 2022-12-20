# Copyright (C) 2019 ANSYS, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
"""
Created on Jan 23, 2014
Updated on Nov 27, 2018
@author: cebutor
modified: adimaria
"""
import os
import socket
import subprocess
import sys
import time

from pyaedt import pyaedt_logger


class WB2Client:
    hostName = ""
    portNumber = 0
    showGui = False

    def __init__(self, port, host, showgui, sWorkbenchVersion):
        self.hostName = host
        self.portNumber = port
        self.showGui = showgui
        self.logger = pyaedt_logger
        self.version = sWorkbenchVersion
        self.pid = None

    """
    Launching Workbench in Server Mode
    """

    def LaunchWorkbenchInServerMode(self):
        # awpVal = os.environ.get("AWP_ROOT192")
        envs = os.environ
        if self.version:
            awpVal = os.environ.get(self.version)
        else:
            awps = []
            for env in envs:
                if "AWP_ROOT" in env:
                    awps.append(env)
            awpVal = os.environ.get(max(awps))
        frwkInstallPath = os.path.join(awpVal, os.path.join("Framework", os.path.join("bin", "Win64")))
        wbExe = "RunWB2.exe"
        wbExeFullPath = os.path.join(frwkInstallPath, wbExe)
        # start wb2 in server mode.
        self.logger.debug(
            "Starting ANSYS Workbench with a listening server on " + self.hostName + ":" + str(self.portNumber)
        )
        appArgs = [wbExeFullPath, "-P", str(self.portNumber), "-H", self.hostName]

        if self.showGui is not True:
            appArgs.append("-nowindow")
            appArgs.append("-B")
        process = subprocess.Popen(appArgs)
        # sleep for 10 seconds to allow WB to start up.
        time.sleep(1.0)
        # wait for WB to respond (for 120 seconds)
        self.wait_for_healthy_connection()
        self.pid = process.pid
        return process.pid

    def wait_for_healthy_connection(self):
        # wait for WB to respond (for 180 seconds)
        counter = 60
        attempt = 1
        wb_up_and_running = False
        while counter > 0:
            self.logger.debug(f"Waiting WB to open. Testing the connection ({attempt} attempt).")
            socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                socket1.connect((self.hostName, self.portNumber))
            except Exception as e:
                socket1.close()
            else:
                cmd = "GetProjectUnitSystem"
                socket1.send(cmd.encode())
                socket1.send("<EOF>".encode())
                # wait for reply from server.
                mssgRcvd = socket1.recv(4096).decode()
                socket1.close()
                if mssgRcvd == "<OK>":
                    wb_up_and_running = True

            if not wb_up_and_running:
                self.logger.debug("Connection failed.")
                counter -= 1
                attempt += 1
                time.sleep(3)  # retries the connection every 3 seconds
            else:
                self.logger.debug("Connection established.")
                time.sleep(3)
                break
        if not wb_up_and_running:
            raise Exception("Cannot establish a connection with Workbench.")
        return True

    def CloseWorkbench(self):
        socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket1.connect((self.hostName, self.portNumber))
        # send termination to server since we're done....typically we would keep the session
        # up for other connections...but close it for this example.
        self.logger.debug("Sending Exit to Workbench")
        socket1.send("Exit\n<EOF>".encode())
        self.logger.debug("Client finished.")
        self.logger.info("Sending Exit to Workbench")
        socket1.close()
        # in case WB won't close, sends a kill signal after 5 seconds
        time.sleep(10)

    def GetVariableValue(self, variablename):
        socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = True
        try:
            self.logger.info("Establishing connection to server: " + self.hostName + ":" + str(self.portNumber))
            socket1.connect((self.hostName, self.portNumber))
        except Exception as e:
            connected = False
            self.logger.error("Error connecting to server.  Details:\n\t" + str(sys.exc_info()) + "\nTry again later.")
            self.logger.error(str(e))

        if connected is True:
            self.logger.info("Connected to WorkBench server.")
            cmd = "Query," + variablename
            socket1.send(cmd.encode())
            socket1.send("<EOF>".encode())
            # wait for reply from server.
            mssgRcvd = socket1.recv(4096).decode()
            self.logger.info("Reply from server: " + mssgRcvd)
            socket1.close()

            returnVal = None
            if mssgRcvd.find(variablename + "=") != -1:
                returnVal = mssgRcvd.replace(variablename + "=", "")
            return returnVal

    def SendScriptStatement(self, statement):
        socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = True
        try:
            # self.logger.info("Establishing connection to server: "+self.hostName+":"+str(self.portNumber))
            socket1.connect((self.hostName, self.portNumber))
        except Exception as e:
            connected = False
            self.logger.error("Error connecting to server.  Details:\n\t" + str(sys.exc_info()) + "\nTry again later.")
            self.logger.error("Error while executing \n\t " + statement)
            self.logger.error(str(e))
        if connected is True:
            # self.logger.info("Connected to WorkBench server.")
            cmd = statement
            socket1.send(cmd.encode())
            socket1.send("<EOF>".encode())
            # wait for reply from server.
            mssgRcvd = socket1.recv(4096).decode()
            socket1.close()

            if mssgRcvd == "<OK>":
                self.logger.debug("Successful Transmission.")
            else:
                self.logger.debug("Error Transmitting command: " + cmd)
                self.logger.error("Transmission failed.  Check server reply for details.")
                self.logger.error(cmd)

            return mssgRcvd

    def SendScriptFile(self, filepath):
        socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = True
        try:
            self.logger.debug("Establishing connection to server: " + self.hostName + ":" + str(self.portNumber))
            socket1.connect((self.hostName, self.portNumber))
        except Exception as e:
            connected = False
            self.logger.debug("Error connecting to server.  Details:\n\t" + str(sys.exc_info()) + "\nTry again later.")
            self.logger.error(str(e))
        if connected is True:
            self.logger.debug("Connected to server.")

            with open(filepath, "r") as scriptFile:
                for currLine in scriptFile:
                    cmd = currLine
                    self.logger.debug("Sending message: " + cmd[:-1])
                    socket1.send(cmd.encode())

            self.logger.info("Sending <EOF> to server.")
            socket1.send("<EOF>".encode())
            # wait for reply from server.
            mssgRcvd = socket1.recv(4096).decode()
            self.logger.debug("  Reply from server: " + mssgRcvd)
            socket1.close()

            if mssgRcvd == "<OK>":
                self.logger.debug("Successful Transmission.")
            else:
                self.logger.error("Transmission failed.  Check server reply for details.")
                self.logger.error(cmd)
                # note - client connection is terminated by server after EOF...any future transmission from
            # client to server will require a new socket instance and connection.


# example API calls:
#
# client = WB2Client(8001, "localhost", True)
# client.LaunchWorkbenchInServerMode()
# client.SendScriptFile(r"C:\WorkbenchServerPackage_2019R1\exampleScript.py")
# client.SendScriptStatement("system1Name = system1.Name")
# system1Name = client.GetVariableValue("system1Name")
# if system1Name != None:
#    print system1Name
# client.SendScriptStatement("Reset()")
# client.CloseWorkbench()
