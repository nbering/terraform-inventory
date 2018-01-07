#! /usr/bin/env python2

import json
import os
import re
import subprocess
import sys

TERRAFORM_PATH = os.environ.get('TERRAFORM_PATH', 'terraform')

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

def _add_host(inventory, hostname, groups, host_vars):
    inventory["_meta"]["hostvars"][hostname] = host_vars
    for group in groups:
        if group not in inventory.keys():
            inventory[group] = [hostname]
        elif hostname not in inventory[group]:
            inventory[group].append(hostname)

def _init_inventory():
    return {
        "all": [],
        "_meta": {
            "hostvars": {}
        }
    }

def _walk_state(tfstate, inventory):
    for module in tfstate["modules"]:
        for resource in module["resources"].values():
            if resource["type"] != "ansible_host":
                continue
            
            attrs = resource["primary"]["attributes"]

            host_vars = _extract_dict(attrs, "vars")
            groups = _extract_list(attrs, "groups")
            hostname = attrs["inventory_hostname"]

            if "all" not in groups:
                groups.append("all")

            _add_host(inventory, hostname, groups, host_vars)
    return inventory

def _main():
    try:
        proc = subprocess.Popen([TERRAFORM_PATH, 'state', 'pull'], stdout=subprocess.PIPE)
        tfstate = json.load(proc.stdout)
        inventory = _walk_state(tfstate, _init_inventory())
        sys.stdout.write(json.dumps(inventory, indent=2))
    except:
        sys.exit(1)

if __name__ == '__main__':
    _main()
