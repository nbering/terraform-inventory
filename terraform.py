#!/usr/bin/env python

'''
Terraform Inventory Script
==========================
This inventory script generates dynamic inventory by reading Terraform state
contents. Servers and groups a defined inside the Terraform state using special
resources defined by the Terraform Provider for Ansible.

Configuration
=============

State is fetched using the "terraform state pull" subcommand. The behaviour of
this action can be configured using some environment variables.

Environment Variables:
......................

    ANSIBLE_TF_BIN
        Override the path to the Terraform command executable. This is useful if
        you have multiple copies or versions installed and need to specify a
        specific binary. The inventory script runs the `terraform state pull`
        command to fetch the Terraform state, so that remote state will be
        fetched seemlessly regardless of the backend configuration.

    ANSIBLE_TF_DIR
        Set the working directory for the `terraform` command when the scripts
        shells out to it. This is useful if you keep your terraform and ansible
        configuration in separate directories. Defaults to using the current
        working directory.

    ANSIBLE_TF_WS_NAME
        Sets the workspace for the `terraform` command when the scripts shells
        out to it, defaults to `default` workspace - if you don't use workspaces
        this is the one you'll be using.
'''

import sys
import json
import os
import re
import traceback
from subprocess import Popen, PIPE

TERRAFORM_PATH = os.environ.get('ANSIBLE_TF_BIN', 'terraform')
TERRAFORM_DIR = os.environ.get('ANSIBLE_TF_DIR', os.getcwd())
TERRAFORM_WS_NAME = os.environ.get('ANSIBLE_TF_WS_NAME', 'default')


class TerraformState(object):
    def __init__(self, state_json):
        self.state_json = state_json

        if "modules" in state_json:
            # uses pre-0.12
            self.flat_attrs = True
        else:
            # state format for 0.12+
            self.flat_attrs = False

    def resources(self):
        if self.flat_attrs:
            modules = self.state_json["modules"]
            for module in modules:
                for resource in module["resources"].values():
                    yield TerraformResource(resource, flat_attrs=True)
        else:
            resources = self.state_json["resources"]
            for resource in resources:
                for instance in resource["instances"]:
                    yield TerraformResource(instance, resource_type=resource["type"])


class TerraformResource(object):
    def __init__(self, source_json, flat_attrs=False, resource_type=None):
        self.flat_attrs = flat_attrs
        self._type = resource_type
        self.source_json = source_json

    def is_ansible(self):
        return self.type().startswith("ansible_")

    def type(self):
        if self._type:
            return self._type
        return self.source_json["type"]

    def read_dict_attr(self, key):
        attrs = self._raw_attributes()

        if self.flat_attrs:
            out = {}
            for k in attrs.keys():
                match = re.match(r"^" + key + r"\.(.*)", k)
                if not match or match.group(1) == "%":
                    continue

                out[match.group(1)] = attrs[k]
            return out
        return attrs.get(key, {})

    def read_list_attr(self, key):
        attrs = self._raw_attributes()

        if self.flat_attrs:
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
        return attrs.get(key, None)

    def read_attr(self, key):
        return self._raw_attributes().get(key, None)

    def _raw_attributes(self):
        if self.flat_attrs:
            return self.source_json["primary"]["attributes"]
        return self.source_json["attributes"]


class AnsibleInventory(object):
    def __init__(self):
        self.groups = {}
        self.hosts = {}
        self.inner_json = {}

    def update_hosts(self, hostname, groups=None, host_vars=None):
        if hostname in self.hosts:
            host = self.hosts[hostname]
            host.update(groups=groups, host_vars=host_vars)
        else:
            host = AnsibleHost(hostname, groups=groups, host_vars=host_vars)
            self.hosts[hostname] = host

        if host.groups:
            for groupname in host.groups:
                self.update_groups(groupname, hosts=[hostname])

    def update_groups(self, groupname, children=None, hosts=None, group_vars=None):
        if groupname in self.groups:
            self.groups[groupname].update(
                children=children, hosts=hosts, group_vars=group_vars)
        else:
            self.groups[groupname] = AnsibleGroup(
                groupname, children=children, hosts=hosts, group_vars=group_vars)

    def add_host_resource(self, resource):
        hostname = resource.read_attr("inventory_hostname")
        groups = resource.read_list_attr("groups")
        host_vars = resource.read_dict_attr("vars")

        self.update_hosts(hostname, groups=groups, host_vars=host_vars)

    def add_host_var_resource(self, resource):
        hostname = resource.read_attr("inventory_hostname")
        key = resource.read_attr("key")
        value = resource.read_attr("value")

        host_vars = {key: value}

        self.update_hosts(hostname, host_vars=host_vars)

    def add_group_resource(self, resource):
        groupname = resource.read_attr("inventory_group_name")
        children = resource.read_list_attr("children")
        group_vars = resource.read_dict_attr("vars")

        self.update_groups(groupname, children=children, group_vars=group_vars)

    def add_group_var_resource(self, resource):
        groupname = resource.read_attr("inventory_group_name")
        key = resource.read_attr("key")
        value = resource.read_attr("value")

        group_vars = {key: value}

        self.update_groups(groupname, group_vars=group_vars)

    def add_resource(self, resource):
        if resource.type() == "ansible_host":
            self.add_host_resource(resource)
        elif resource.type() == "ansible_host_var":
            self.add_host_var_resource(resource)
        elif resource.type() == "ansible_group":
            self.add_group_resource(resource)
        elif resource.type() == "ansible_group_var":
            self.add_group_var_resource(resource)

    def to_dict(self):
        out = {
            "_meta": {
                "hostvars": {}
            }
        }

        for hostname, host in self.hosts.items():
            host.tidy()
            out["_meta"]["hostvars"][hostname] = host.get_vars()

        for groupname, group in self.groups.items():
            group.tidy()
            out[groupname] = group.to_dict()

        return out


class AnsibleHost(object):
    def __init__(self, hostname, groups=None, host_vars=None):
        self.hostname = hostname
        self.groups = set(["all"])
        self.host_vars = {}

        self.update(groups=groups, host_vars=host_vars)

    def update(self, groups=None, host_vars=None):
        if host_vars:
            self.host_vars.update(host_vars)
        if groups:
            self.groups.update(groups)

    def tidy(self):
        self.groups = sorted(self.groups)

    def get_vars(self):
        return dict(self.host_vars)


class AnsibleGroup(object):
    def __init__(self, groupname, children=None, hosts=None, group_vars=None):
        self.groupname = groupname
        self.hosts = set()
        self.children = set()
        self.group_vars = {}

        self.update(children=children, hosts=hosts, group_vars=group_vars)

    def update(self, children=None, hosts=None, group_vars=None):
        if hosts:
            self.hosts.update(hosts)
        if children:
            self.children.update(children)
        if group_vars:
            self.group_vars.update(group_vars)

    def tidy(self):
        self.hosts = sorted(self.hosts)
        self.children = sorted(self.children)

    def to_dict(self):
        return {
            "children": list(self.children),
            "hosts": list(self.hosts),
            "vars": dict(self.group_vars)
        }


def _execute_shell():
    encoding = 'utf-8'
    tf_workspace = [TERRAFORM_PATH, 'workspace', 'select', TERRAFORM_WS_NAME]
    proc_ws = Popen(tf_workspace, cwd=TERRAFORM_DIR, stdout=PIPE,
                    stderr=PIPE, universal_newlines=True)
    _, err_ws = proc_ws.communicate()
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
            return json.loads(out_cmd, encoding=encoding)


def _main():
    try:
        tfstate = TerraformState(_execute_shell())
        inventory = AnsibleInventory()

        for resource in tfstate.resources():
            if resource.is_ansible():
                inventory.add_resource(resource)

        sys.stdout.write(json.dumps(inventory.to_dict(), indent=2))
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    _main()
