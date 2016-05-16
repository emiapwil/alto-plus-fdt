#!/bin/env python3

import subprocess

FDT_DEFAULT_PORT = 54321

FDT_STATUS_WAITING = "WAITING"
FDT_STATUS_RUNNING = "RUNNING"
FDT_STATUS_FINISHED = "FINISHED"
FDT_STATUS_PENDING = "PENDING"
FDT_STATUS_FAILED = "FAILED"

class FDTNode(object):
    """
    Base class for FDT servers/clients
    """

    def __init__(self, uuid, ip_addr, port = None):
        self.uuid = uuid
        self.ip_addr = ip_addr
        self.port = port

    def start(self):
        """
        Start the node
        """
        pass

    def uuid(self):
        return self.uuid

    def ip_addr(self):
        return self.ip_addr

    def port(self):
        return self.port


class FDTServer(FDTNode):
    """
    FDT server node
    """

    def __init__(self, uuid, ip_addr, port = None, id_file = None, *options):
        FDTNode.__init__(self, uuid, ip_addr, port)

    def start(self):
        cmd = ["ssh"]
        if id_file is not None:
            cmd +=
        remote_cmd = "java -jar /opt/fdt/fdt.jar -p %d -v -printStat" % self.port
        subprocess.call(["ssh", "%s@%s"%("fdt", self.ip_addr), cmd])

class Task(object):
    """
    Wrapper of a task
    """

    def __init__(self, server_ip, client_ip, filenames,
                        server_port = FDT_DEFAULT_PORT)
        """
        Create a task object
        """
        self.server_ip = server_ip
        self.client_ip = client_ip

        self.server_port = server_port

        self.filenames = filenames

        self.status = FDT_STATUS_WAITING
        self.progress = 0
        self.current_speed = None
        self.rate_limit = None

    def status(self):
        return self.status

    def progress(self):
        return self.progress

    def setup_server(self):
        subprocess
