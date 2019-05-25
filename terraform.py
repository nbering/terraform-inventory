#!/usr/bin/env python

import bisect
import sys
import json
import os
import re
from subprocess import Popen, PIPE

TERRAFORM_PATH = os.environ.get('ANSIBLE_TF_BIN', 'terraform')
TERRAFORM_DIR = os.environ.get('ANSIBLE_TF_DIR', os.getcwd())
TERRAFORM_WS_NAME = os.environ.get('ANSIBLE_TF_WS_NAME', 'default')


def _extract_dict(attrs, key):
    out = {}
    for k in attrs.keys():
        match = re.match(r"^" + key + r"\.(.*)", k)
        if not match or match.group(1) == "%":
            continue

        out[match.group(1)] = attrs[k]
    return out


def _extract_list(attrs, key):
    out = []

    length_key = key + ".#"
    if length_key not in attrs.keys():
        return []

    length = int(attrs[length_key])
    if length < 1:
        return []

    for i in range(0, length):
        out.append(attrs["{}.{}".format(key, i)])

    return out


def _init_group(children=None, hosts=None, vars=None):
    if children is None:
        children = []
    if hosts is None:
        hosts = []
    if vars is None:
        vars = {}

    return {
        "hosts": sorted(hosts),
        "vars": vars,
        "children": sorted(children)
    }


def _add_host(inventory, hostname, groups, host_vars):
    if host_vars is None:
        host_vars = {}
    if groups is None:
        groups = []

    if "all" not in groups:
        groups.append("all")

    if not hostname in inventory["_meta"]["hostvars"]:
        # make a copy because subsequent calls are going to mutate the instance
        inventory["_meta"]["hostvars"][hostname] = host_vars.copy()
    else:
        inventory["_meta"]["hostvars"][hostname].update(host_vars)


    for group in groups:
        if group not in inventory.keys():
            inventory[group] = _init_group(hosts=[hostname])
        elif hostname not in inventory[group]["hosts"]:
            bisect.insort(inventory[group]["hosts"], hostname)


def _add_group(inventory, group_name, children, group_vars):
    if children is None:
        children = []
    if group_name not in inventory.keys():
        inventory[group_name] = _init_group(children=children, vars=group_vars)
    else:
        # Start out with support for only one "group" with a given name
        # If there's a second group by the name, last in wins
        inventory[group_name]["children"] = sorted(children)
        inventory[group_name]["vars"] = group_vars


def _init_inventory():
    return {
        "all": _init_group(),
        "_meta": {
            "hostvars": {}
        }
    }


def _handle_host(attrs, inventory):
    host_vars = _extract_dict(attrs, "vars")
    groups = _extract_list(attrs, "groups")
    hostname = attrs["inventory_hostname"]

    _add_host(inventory, hostname, groups, host_vars)


def _handle_host_var(attrs, inventory):
    host_vars = {attrs["key"]: attrs["value"]}
    hostname = attrs["inventory_hostname"]

    _add_host(inventory, hostname, None, host_vars)

def _handle_group_var(attrs, inventory):
    group_vars = {attrs["key"]: attrs["value"]}
    group_name = attrs["inventory_group_name"]

    _add_group(inventory, group_name, None, group_vars)

def _handle_group(attrs, inventory):
    group_vars = _extract_dict(attrs, "vars")
    children = _extract_list(attrs, "children")
    group_name = attrs["inventory_group_name"]

    _add_group(inventory, group_name, children, group_vars)


def _walk_state(tfstate, inventory):
    if "modules" in tfstate:
        # handle Terraform < 0.12
        for module in tfstate["modules"]:
            for resource in module["resources"].values():
                if not resource["type"].startswith("ansible_"):
                    continue

                attrs = resource["primary"]["attributes"]

                if resource["type"] == "ansible_host":
                    _handle_host(attrs, inventory)
                elif resource["type"] == "ansible_group":
                    _handle_group(attrs, inventory)
                elif resource["type"] == "ansible_group_var":
                    _handle_group_var(attrs, inventory)
                elif resource["type"] == "ansible_host_var":
                    _handle_host_var(attrs, inventory)
    else:
        # handle Terraform >= 0.12
        for resource in tfstate["resources"]:
            if resource["provider"] != "provider.ansible":
                continue

            for instance in resource["instances"]:
                attrs = instance["attributes"]

                if resource["type"] == "ansible_group":
                    _add_group(
                        inventory, attrs["inventory_group_name"], attrs["children"], attrs["vars"])
                elif resource["type"] == "ansible_group_var":
                    _add_group(
                        inventory, attrs["inventory_group_name"], None, {attrs["key"]: attrs["value"]})
                elif resource["type"] == "ansible_host":
                    _add_host(
                        inventory, attrs["inventory_hostname"], attrs["groups"], attrs["vars"])
                elif resource["type"] == "ansible_host_var":
                    _add_host(
                        inventory, attrs["inventory_hostname"], None, {attrs["key"]: attrs["value"]})

    return inventory


def _execute_shell():
    encoding = 'utf-8'
    tf_workspace = [TERRAFORM_PATH, 'workspace', 'select', TERRAFORM_WS_NAME]
    proc_ws = Popen(tf_workspace, cwd=TERRAFORM_DIR, stdout=PIPE,
                    stderr=PIPE, universal_newlines=True)
    out_ws, err_ws = proc_ws.communicate()
    if err_ws != '':
        sys.stderr.write(str(err_ws)+'\n')
        sys.exit(1)
    else:
        tf_command = [TERRAFORM_PATH, 'state', 'pull']
        proc_tf_cmd = Popen(tf_command, cwd=TERRAFORM_DIR,
                            stdout=PIPE, stderr=PIPE, universal_newlines=True)
        out_cmd, err_cmd = proc_tf_cmd.communicate()
        if err_cmd != '':
            sys.stderr.write(str(err_cmd)+'\n')
            sys.exit(1)
        else:
            return json.loads(out_cmd, encoding='utf-8')


def _main():
    try:
        tfstate = _execute_shell()
        inventory = _walk_state(tfstate, _init_inventory())
        sys.stdout.write(json.dumps(inventory, indent=2))
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.exit(1)


if __name__ == '__main__':
    _main()
