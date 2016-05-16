#!/bin/env python3

from bottle import route, run, request, abort
from subprocess import Popen, STDOUT, PIPE
import re
import json
import threading

from .common import install_fdt, get_fdt_cfg, fdt_jar_name, data_dir

fdt_client_cfg = {}
tasks = {}

UUID_PATTERN="[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
INIT_PATTERN=".*(%s) initialized" % UUID_PATTERN

def debug(process):
    for line in process.stdout:
        line = line.decode("utf-8")
        print(line)
    return 0

def handle(task, mode, target):
    global tasks, fdt_client_cfg

    server_ip = task["server"]["ip"]
    server_port = task["server"]["port"]
    files = task["files"]

    fdt_jar = fdt_jar_name()

    cmd = ["java"]
    cmd += ["-jar", fdt_jar]
    cmd += ["-c", server_ip, "-p", "%d" % server_port]
    cmd += ["-pull"] if mode == 'pull' else []
    cmd += ["-d", target]
    cmd += files

    try:
        process = Popen(cmd, stderr=STDOUT, stdout=PIPE)
        task["process"] = process
        for line in process.stdout:
            line = line.decode("utf-8")
            m = re.search(INIT_PATTERN, line)
            print(line)
            if m is not None:
                uuid = m.group(1)

                tasks[uuid] = task
                debugging = lambda : debug(process)
                thread = threading.Thread(target=debugging)
                thread.start()
                return {"uuid": uuid}
        abort(400, "Failed to start transfer")
    except Exception as e:
        raise e
        abort(400, "Failed to start transfer")

@route("/pull", method="POST")
def pull_data():
    data = request.body.read()
    print(data.decode("utf-8"))
    task = json.loads(data.decode("utf-8"))
    return handle(task, "pull", task["target"])

@route("/push", method="POST")
def push_data():
    task = json.loads(request.body.read().decode("utf-8"))
    return handle(task, "push", task["target"])

@route("/cancel", method="POST")
def cancel():
    uuid = json.loads(request.body.read().decode("utf-8"))["uuid"]
    if uuid in tasks:
        task = tasks[uuid]
        del tasks[uuid]

        try:
            task["process"].kill()
        except Exception as e:
            pass

if __name__ == '__main__':
    global fdt_client_cfg

    hostname, ip, port = get_fdt_cfg("client", 6667)
    try:
        install_fdt()

        fdt_client_cfg = {"ip": ip}
        run(host=hostname, port = port, debug=True)
    except Exception as e:
        raise e
