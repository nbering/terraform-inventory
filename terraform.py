#! /usr/bin/env python2

import json
import os
import re
import subprocess
import sys

TERRAFORM_PATH = os.environ.get('ANSIBLE_TF_BIN', 'terraform')
TERRAFORM_DIR = os.environ.get('ANSIBLE_TF_DIR', os.getcwd())

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
    return {
        "hosts": [] if hosts is None else hosts,
        "vars": {} if vars is None else vars,
        "children": [] if children is None else children
    }

def _add_host(inventory, hostname, groups, host_vars):
    inventory["_meta"]["hostvars"][hostname] = host_vars
    for group in groups:
        if group not in inventory.keys():
            inventory[group] = _init_group(hosts=[hostname])
        elif hostname not in inventory[group]:
            inventory[group]["hosts"].append(hostname)

def _add_group(inventory, group_name, children, group_vars):
    if group_name not in inventory.keys():
        inventory[group_name] = _init_group(children=children, vars=group_vars)
    else:
        # Start out with support for only one "group" with a given name
        # If there's a second group by the name, last in wins
        inventory[group_name]["children"] = children
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

    if "all" not in groups:
        groups.append("all")

    _add_host(inventory, hostname, groups, host_vars)

def _handle_group(attrs, inventory):
    group_vars = _extract_dict(attrs, "vars")
    children = _extract_list(attrs, "children")
    group_name = attrs["inventory_group_name"]

    _add_group(inventory, group_name, children, group_vars)

def _walk_state(tfstate, inventory):
    for module in tfstate["modules"]:
        for resource in module["resources"].values():
            if not resource["type"].startswith("ansible_"):
                continue

            attrs = resource["primary"]["attributes"]

            if resource["type"] == "ansible_host":
                _handle_host(attrs, inventory)
            if resource["type"] == "ansible_group":
                _handle_group(attrs, inventory)

    return inventory

def _main():
    try:
        tf_command = [TERRAFORM_PATH, 'state', 'pull', '-input=false']
        proc = subprocess.Popen(tf_command, cwd=TERRAFORM_DIR, stdout=subprocess.PIPE)
        tfstate = json.load(proc.stdout)
        inventory = _walk_state(tfstate, _init_inventory())
        sys.stdout.write(json.dumps(inventory, indent=2))
    except:
        sys.exit(1)

if __name__ == '__main__':
    _main()
