#!/bin/env python3

import os.path
import logging
from daemonize import Daemonize

def pyfdt_info(msg):
    print("[PyFDT]: %s" % msg)

def base_dir():
    import os
    return os.path.dirname(os.path.realpath(__file__)) + "/"

def lib_dir():
    return base_dir() + "lib/"

def run_dir():
    return base_dir() + "run/"

def fdt_jar_name():
    return lib_dir() + "fdt.jar"

def pid_file_name():
    return run_dir() + "pyfdt.pid"

def log_file_name():
    return run_dir() + "pyfdt.log"

def install_fdt():
    os.makedirs(lib_dir(), exist_ok = True)

    if os.path.isfile(fdt_jar_name()):
        return

    import urllib.request
    source_url = "http://monalisa.cern.ch/FDT/lib/fdt.jar"
    urllib.request.urlretrieve(source_url, fdt_jar_name())

from bottle import route, run, abort

fdt_server_cfg = { 'port': 54321 }
process = None
logfile = None
analyzer = None
stat = {}

UUID_PATTERN= "[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
IPV4_PATTERN= "[0-9\.]+"
PORT_PATTERN= "[0-9]+"
SESSION_PATTERN = ".*FDTSession \( (%s) \).*Socket\[addr=/(%s),port=(%s),localport=(%s)\].*"

def clean_up():
    if logfile is not None:
        logfile.close()
        logfile = None
    if process is not None:
        process.kill()

def analyze_fdt_log():
    import re
    global process, analyzer, logfile, stat

    try:
        logfile = open(log_file_name(), "wb")
        for line in process.stdout:
            logfile.write(line)

            p =  SESSION_PATTERN % (UUID_PATTERN, IPV4_PATTERN, PORT_PATTERN, PORT_PATTERN)
            line = line.decode("utf-8")
            m = re.search(p, line)
            if m is not None and len(m.groups()) == 4:
                uuid = m.group(1)

                remote_ip = m.group(2)
                remote_port = m.group(3)

                local_ip = fdt_server_cfg['ip']
                local_port = m.group(4)

                if re.search('started', line) is not None:
                    client = {"ip": remote_ip, "port": remote_port}
                    server = {"ip": local_ip, "port": local_port}
                    status = "running"
                    stat[uuid] = { "client": client, "server": server, "status": status }
                elif re.search('finished', line) is not None:
                    if uuid in stat:
                        stat[uuid]["status"] = "finished"

                print(line)

    except Exception as e:
        logfile.close()
        logfile = None
        analyzer = None
        raise e

@route('/start')
def start_fdt():
    port = fdt_server_cfg['port']

    install_fdt()

    fdt_jar = fdt_jar_name()
    cmd = ["java"]
    cmd += ["-jar", "%s" % fdt_jar]
    cmd += [ "-p", "%d" % port ]
    cmd += [ "-v", "-printStat" ]

    from subprocess import Popen, STDOUT, PIPE
    import threading

    try:
        global process
        process = Popen(cmd, stderr=STDOUT, stdout=PIPE)

        analyzer = threading.Thread(target=analyze_fdt_log)
        analyzer.start()
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
    try:
        fdt_server_cfg["ip"] = "127.0.0.1"
        run(host='localhost', port=6666, debug=True)
    except Exception as e:
        clean_up()
