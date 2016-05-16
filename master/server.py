#!/bin/env python3

from bottle import route, abort, run, request
import json
import requests

SERVER_PORT = 6666
CLIENT_PORT = 6667

servers = {}
clients = {}
tasks = {}
task_meta = {}
timeout = 5000 # 5000ms
watcher = None

def gather_stat():
    global servers, tasks
    import time

    while watcher is not None:
        time.sleep(timeout / 1000.0)

        new_tasks = tasks.copy()
        for uuid, task in new_tasks.items():
            task["stat"] = {}

        for _, server in servers.items():
            if server["monitored"] != "on":
                continue

            try:
                url = "http://%s:%d/status" % (server['hostname'], server['port'])
                r = requests.get(url)
                data = r.json()

                for uuid, stat in data.items():
                    if uuid in new_tasks:
                        new_tasks[uuid]["stat"] = stat
            except Exception as e:
                print(e)
                pass
        tasks = new_tasks

def create_monitor(server):
    server["monitored"] = "on"

def stop_monitor(server):
    server["monitored"] = "off"

def start_server(server):
    try:
        url = "http://%s:%d/start" % (server['hostname'], server['port'])
        r = requests.get(url)
        server["started"] = (r.status_code == 200)

        create_monitor(server)
    except Exception as e:
        raise e

def stop_server(server):
    try:
        if server["started"] == False:
            return
        url = "http://%s:%d/stop" % (server['hostname'], server['port'])
        r = requests.get(url)
        if r.status_code == 200:
            return
        else:
            abort(400, "Failed to stop remote server")

        stop_monitor(server)
    except Exception as e:
        raise e

def process_fdt(server, port):
    hostname = server.get('hostname', None)
    if hostname is None:
        abort(400, "Need hostname")
    from socket import gethostbyname
    server["ip"] = gethostbyname(hostname)

    port = server.get('port', port)
    server['port'] = port

    key = "%s:%d" % (hostname, port)

@route("/server/add", method='POST')
def add_server():
    global servers

    data = request.body.read()
    server = json.loads(data.decode("utf-8"))

    key = process_fdt(server, SERVER_PORT)
    if key in servers:
        return

    start_server(server)
    servers[key] = server

@route("/server/remove", method='POST')
def remove_server():
    global servers

    data = request.body.read().decode("utf-8")
    server = json.loads(data)

    key = process_fdt(server, SERVER_PORT)
    if not key in servers:
        return

    server = servers[key]
    del servers[key]
    stop_server(server)

@route("/client/add", method='POST')
def add_client():
    global clients

    data = request.body.read()
    client = json.loads(data.decode("utf-8"))

    key = process_fdt(client, CLIENT_PORT)

    if key in clients:
        return

    clients[key] = client

@route("/client/remove", method='POST')
def remove_client():
    global clients

    data = request.body.read().decode("utf-8")
    client = json.loads(data)

    key = process_fdt(client, CLIENT_PORT)
    if not key in clients:
        return

    client = clients[key]
    del clients[key]

@route("/task/submit", method="POST")
def add_task():
    global clients, servers

    data = json.loads(request.body.read().decode("utf-8"))
    key_server = process_fdt(data["server"], SERVER_PORT)
    key_client = process_fdt(data["client"], CLIENT_PORT)
    files = data["files"]
    target = data["target"]

    server = servers[key_server]
    client = clients[key_client]

    try:
        url = "http://%s:%d/pull" % (client["hostname"], client["port"])
        post_data = {"server": {"ip": server["ip"], "port": 54321}}
        post_data.update({"files":list(files)})
        post_data.update({"target":target})

        r = requests.post(url, json.dumps(post_data))
        if r.status_code == 200:
            task = r.json()
            tasks[task["uuid"]] = {}
            task_meta[task["uuid"]] = data
    except Exception as e:
        raise e

@route("/task/cancel", method="POST")
def remove_task():
    global clients, servers

    data = json.loads(request.body.read().decode("utf-8"))
    uuid = data["uuid"]
    task = task_meta[uuid]

    key_client = process_fdt(task["client"], CLIENT_PORT)
    client = clients[key_client]

    try:
        url = "http://%s:%d/cancel" % (client["hostname"], client["port"])
        post_data = {"uuid": uuid}

        r = requests.post(url, json.dumps(post_data))
        if r.status_code == 200:
            return
        abort(r.status_code, r.text)
    except Exception as e:
        raise e

@route("/task/status")
def get_task_status():
    return tasks


if __name__ == '__main__':
    try:
        import threading, sys

        hostname = sys.argv[1]

        watcher = threading.Thread(target=gather_stat)
        watcher.start()

        run(host = hostname, port=6665, debug=True)
    except Exception as e:
        for _, server in servers.items():
            stop_server(server)

        watcher = None
