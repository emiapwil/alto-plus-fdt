#!/bin/env python3

import logging
from daemonize import Daemonize
import re
from bottle import route, run, abort

from .common import log_file_name, fdt_jar_name, install_fdt, get_fdt_cfg, data_dir

fdt_server_cfg = {}
process = None
logfile = None
analyzer = None
stat = {}

def clean_up():
    global logfile, process
    if logfile is not None:
        logfile.close()
        logfile = None
    if process is not None:
        process.kill()

UUID_PATTERN="[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
IPV4_PATTERN="[0-9\.]+"
PORT_PATTERN="[0-9]+"

START_PATTERN=".*FDTSession \( (%s) \).*\[addr=/(%s),port=(%s),localport=(%s)\].*started"
END_PATTERN=".*(%s).*finished (\w+).*"

def analyze_session_start(line):
    p =  START_PATTERN % (UUID_PATTERN, IPV4_PATTERN, PORT_PATTERN, PORT_PATTERN)
    m = re.search(p, line)

    if m is not None and len(m.groups()) == 4:
        uuid = m.group(1)

        remote_ip = m.group(2)
        remote_port = m.group(3)

        local_ip = fdt_server_cfg['ip']
        local_port = m.group(4)

        client = {"ip": remote_ip, "port": remote_port}
        server = {"ip": local_ip, "port": local_port}
        status = "running"
        stat[uuid] = { "client": client, "server": server, "status": status }

def analyze_session_end(line):
    p = END_PATTERN % (UUID_PATTERN)
    m = re.search(p, line)

    if m is not None:
        uuid = m.group(1)
        result = m.group(2)
        if uuid in stat:
            stat[uuid]["status"] = "successful" if result == 'OK' else "failed"

BANDWIDTH_PATTERN="[0-9]*\.[0-9]* [MKG]b/s"
TASK_BANDWIDTH_PATTERN="(.*)Net Out: (%s).*Avg: (%s)(.*)"
UUID_TASK_BANDWIDTH="(%s)Net Out: (%s).*Avg: (%s)"

def analyze_process(line):
    global stat

    p = TASK_BANDWIDTH_PATTERN % (BANDWIDTH_PATTERN, BANDWIDTH_PATTERN)

    m = re.search(p, line)
    if m is not None and len(m.groups()) >= 3:
        uuid = m.group(1)
        net = m.group(2)
        avg = m.group(3)

        if re.search(UUID_PATTERN, uuid) is None:
            uuid = [k for k in stat.keys()][0]

        stat[uuid]["speed"] = {"net": net, "avg": avg}

        if len(m.groups()) == 4:
            stat[uuid]["progress"] = m.group(4)

def analyze_fdt_log():
    global process, analyzer, logfile, stat

    stat = {}
    try:
        logfile = open(log_file_name(), "wb")
        for line in process.stdout:
            logfile.write(line)

            line = line.decode("utf-8")

            analyze_session_start(line)
            analyze_process(line)
            analyze_session_end(line)

    except Exception as e:
        logfile.close()
        logfile = None
        analyzer = None
        raise e

@route('/start')
def start_fdt():
    global process

    port = fdt_server_cfg['port']

    if process is not None:
        return

    fdt_jar = fdt_jar_name()
    cmd = ["java"]
    cmd += ["-jar", "%s" % fdt_jar]
    cmd += [ "-p", "%d" % port ]
    cmd += [ "-v", "-printStat" ]

    from subprocess import Popen, STDOUT, PIPE
    import threading

    try:
        process = Popen(cmd, stderr=STDOUT, stdout=PIPE)

        analyzer = threading.Thread(target=analyze_fdt_log)
        analyzer.start()

        return data_dir()
    except Exception as e:
        clean_up()
        raise e
        abort(500, "Failed to start the FDT server")

@route('/stop')
def stop_fdt():
    try:
        global process
        if process is not None:
            process.kill()
            process = None
    except Exception as e:
        abort(500, "Failed to stop the FDT server")
        raise e

@route('/status')
def get_fdt_status():
    global process, stat

    if process is None:
        abort(404, "FDT server is not running")

    return stat

if __name__=='__main__':
    hostname, ip, port = get_fdt_cfg("sever", 6666)

    try:
        install_fdt()

        fdt_server_cfg = { "ip": ip, "port": 54321 }

        run(host=hostname, port=port, debug=True)
    except Exception as e:
        clean_up()
        raise e