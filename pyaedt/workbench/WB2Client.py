# Copyright (C) 2019 ANSYS, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential

import os
import socket
import subprocess
import sys
import time

from pyaedt import pyaedt_function_handler
from pyaedt import pyaedt_logger


class WB2Client:
    """This class contains methods to handle the client server connection with Workbench

    example API calls:

    client = WB2Client("localhost", 8001, True, "AWP_ROOT222")
    client.launch_workbench_in_server_mode()
    client.send_script_file(r"C:\WorkbenchServerPackage_2019R1\exampleScript.py")
    client.SendScriptStatement("system1Name = system1.Name")
    system1Name = client.GetVariableValue("system1Name")
    if system1Name != None:
       print system1Name
    client.SendScriptStatement("Reset()")
    client.CloseWorkbench()
    """

    def __init__(self, host, port, non_graphical, wb_version):
        self.hostName = host
        self.portNumber = port
        self.non_graphical = non_graphical
        self.logger = pyaedt_logger
        self.version = wb_version
        self.pid = None

    """
    Launching Workbench in Server Mode
    """

    @pyaedt_function_handler()
    def launch_workbench_in_server_mode(self):
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
        self.logger.debug("Starting Workbench with a listening server on {}:{}".format(self.hostName, self.portNumber))
        appArgs = [wbExeFullPath, "-P", str(self.portNumber), "-H", self.hostName]

        if self.non_graphical:
            appArgs.append("-nowindow")
            appArgs.append("-B")
        process = subprocess.Popen(appArgs)
        # sleep for 2 seconds to allow WB to start up.
        time.sleep(2.0)
        # wait for WB to respond (for 180 seconds)
        if self.wait_for_healthy_connection(timeout=180):
            self.pid = process.pid
            self.logger.debug(
                "Workbench server started on {}:{} with pid {}".format(self.hostName, self.portNumber, self.pid)
            )
            return process.pid
        else:
            raise Exception("Failed to launch Workbench in server mode.")

    @pyaedt_function_handler()
    def wait_for_healthy_connection(self, timeout=120):
        # wait for WB to respond (for 180 seconds)
        t0 = time.time()
        t1 = t0 + timeout / 2
        secs_each_attempt = 2
        attempt = 1
        wb_up_and_running = False
        self.logger.debug("Testing the connection with Workbench.")
        while t1 - t0 < timeout:
            if attempt != 1:
                time.sleep(secs_each_attempt)  # retries the connection every x seconds
            socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                socket1.connect((self.hostName, self.portNumber))
            except Exception:
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
                attempt += 1
                t1 = time.time()
            else:
                time.sleep(3)
                self.logger.debug("Connection with Workbench established after {}s.".format(str(time.time() - t0)))
                return True
        self.logger.error("Cannot establish a connection with Workbench.")
        return False

    @pyaedt_function_handler()
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

    @pyaedt_function_handler()
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

    @pyaedt_function_handler()
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

    @pyaedt_function_handler()
    def send_script_file(self, filepath):
        socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.logger.debug(
                "Establishing connection to Workbench server {}:{}".format(self.hostName, self.portNumber)
            )
            socket1.connect((self.hostName, self.portNumber))
        except Exception as e:
            self.logger.debug("Error connecting to server.  Details:\n\t" + str(sys.exc_info()))
            raise e
        else:
            self.logger.debug("Connected to server. Sending file.")

            with open(filepath, "r") as scriptFile:
                for currLine in scriptFile:
                    cmd = currLine
                    # self.logger.debug("Sending message: " + cmd[:-1])
                    socket1.send(cmd.encode())

            # self.logger.info("Sending <EOF> to server.")
            socket1.send("<EOF>".encode())
            # wait for reply from server.
            mssgRcvd = socket1.recv(4096).decode()
            self.logger.debug("  Reply from server: " + mssgRcvd)
            socket1.close()

            if mssgRcvd == "<OK>":
                self.logger.debug("Successful Transmission.")
                return True
            else:
                raise Exception("Transmission failed.  Check server reply for details.")

            # note - client connection is terminated by server after EOF...any future transmission from
            # client to server will require a new socket instance and connection.
