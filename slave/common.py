#!/bin/env python3

import os.path
import os

def pyfdt_info(msg):
    print("[PyFDT]: %s" % msg)

def base_dir():
    return os.path.dirname(os.path.realpath(__file__)) + "/"

def lib_dir():
    return base_dir() + "lib/"

def data_dir():
    return base_dir() + "data/"

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
    os.makedirs(data_dir(), exist_ok = True)
    os.makedirs(run_dir(), exist_ok = True)

    if os.path.isfile(fdt_jar_name()):
        return

    import urllib.request
    source_url = "http://monalisa.cern.ch/FDT/lib/fdt.jar"
    urllib.request.urlretrieve(source_url, fdt_jar_name())

def get_fdt_cfg(role, port):
    import sys, argparse

    parser = argparse.ArgumentParser(description='Python wrapper for FDT %s' % role)
    parser.add_argument('--port', help='Specify local IP to be used',
                        type=int, default=port)
    parser.add_argument('hostname', help='The host name for the %s' % role)

    args = parser.parse_args(sys.argv[1:])
    hostname, port = args.hostname, args.port

    from socket import gethostbyname
    return hostname, gethostbyname(hostname), port
