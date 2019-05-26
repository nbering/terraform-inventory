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
    '''
    TerraformState wraps the state content to provide some helpers for iterating
    over resources.
    '''

    def __init__(self, state_json):
        self.state_json = state_json

        if "modules" in state_json:
            # uses pre-0.12
            self.flat_attrs = True
        else:
            # state format for 0.12+
            self.flat_attrs = False

    def resources(self):
        '''Generator method to iterate over resources in the state file.'''
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
    '''
    TerraformResource wraps individual resource content and provide some helper
    methods for reading older-style dictionary and list values from attributes
    defined as a single-level map.
    '''
    DEFAULT_PRIORITIES = {
        'ansible_host': 50,
        'ansible_group': 50,
        'ansible_host_var': 60,
        'ansible_group_var': 60
    }

    def __init__(self, source_json, flat_attrs=False, resource_type=None):
        self.flat_attrs = flat_attrs
        self._type = resource_type
        self._priority = None
        self.source_json = source_json

    def is_ansible(self):
        '''Check if the resource is provided by the ansible provider.'''
        return self.type().startswith("ansible_")

    def priority(self):
        '''Get the merge priority of the resource.'''
        if self._priority is not None:
            return self._priority

        priority = 0

        if self.read_int_attr("variable_priority") is not None:
            priority = self.read_int_attr("variable_priority")
        elif self.type() in TerraformResource.DEFAULT_PRIORITIES:
            priority = TerraformResource.DEFAULT_PRIORITIES[self.type()]

        self._priority = priority

        return self._priority

    def type(self):
        '''Returns the Terraform resource type identifier.'''
        if self._type:
            return self._type
        return self.source_json["type"]

    def read_dict_attr(self, key):
        '''
        Read a dictionary attribute from the resource, handling old-style
        Terraform state where maps are stored as multiple keys in the resource's
        attributes.
        '''
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
        '''
        Read a list attribute from the resource, handling old-style Terraform
        state where lists are stored as multiple keys in the resource's
        attributes.
        '''
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

    def read_int_attr(self, key):
        '''
        Read an attribute from state an convert it to type Int.
        '''
        val = self.read_attr(key)

        if val is not None:
            val = int(val)

        return val

    def read_attr(self, key):
        '''
        Read an attribute from the underlaying state content.
        '''
        return self._raw_attributes().get(key, None)

    def _raw_attributes(self):
        if self.flat_attrs:
            return self.source_json["primary"]["attributes"]
        return self.source_json["attributes"]


class AnsibleInventory(object):
    '''
    AnsibleInventory handles conversion from Terraform resource content to
    Ansible inventory entities, and building of the final inventory json.
    '''

    def __init__(self):
        self.groups = {}
        self.hosts = {}
        self.inner_json = {}

    def add_host_resource(self, resource):
        '''Upsert type action for host resources.'''
        hostname = resource.read_attr("inventory_hostname")

        if hostname in self.hosts:
            host = self.hosts[hostname]
            host.add_source(resource)
        else:
            host = AnsibleHost(hostname, source=resource)
            self.hosts[hostname] = host

    def add_group_resource(self, resource):
        '''Upsert type action for group resources.'''
        groupname = resource.read_attr("inventory_group_name")

        if groupname in self.groups:
            group = self.groups[groupname]
            group.add_source(resource)
        else:
            group = AnsibleGroup(groupname, source=resource)
            self.groups[groupname] = group

    def update_groups(self, groupname, children=None, hosts=None, group_vars=None):
        '''Upsert type action for group resources'''
        if groupname in self.groups:
            group = self.groups[groupname]
            group.update(children=children, hosts=hosts, group_vars=group_vars)
        else:
            group = AnsibleGroup(groupname)
            group.update(children, hosts, group_vars)
            self.groups[groupname] = group

    def add_resource(self, resource):
        '''
        Process a Terraform resource, passing to the correct handler function
        by type.
        '''
        if resource.type().startswith("ansible_host"):
            self.add_host_resource(resource)
        elif resource.type().startswith("ansible_group"):
            self.add_group_resource(resource)

    def to_dict(self):
        '''
        Generate the file Ansible inventory structure to be serialized into JSON
        for consumption by Ansible proper.
        '''
        out = {
            "_meta": {
                "hostvars": {}
            }
        }

        for hostname, host in self.hosts.items():
            host.build()
            for group in host.groups:
                self.update_groups(group, hosts=[host.hostname])
            out["_meta"]["hostvars"][hostname] = host.get_vars()

        for groupname, group in self.groups.items():
            group.build()
            out[groupname] = group.to_dict()

        return out


class AnsibleHost(object):
    '''
    AnsibleHost represents a host for the Ansible inventory.
    '''

    def __init__(self, hostname, source=None):
        self.sources = []
        self.hostname = hostname
        self.groups = set(["all"])
        self.host_vars = {}

        if source:
            self.add_source(source)

    def update(self, groups=None, host_vars=None):
        '''Update host resource with additional groups and vars.'''
        if host_vars:
            self.host_vars.update(host_vars)
        if groups:
            self.groups.update(groups)

    def add_source(self, source):
        '''Add a Terraform resource to the sources list.'''
        self.sources.append(source)

    def build(self):
        '''Assemble host details from registered sources.'''
        self.sources.sort(key=lambda source: source.priority())
        for source in self.sources:
            if source.type() == "ansible_host":
                groups = source.read_list_attr("groups")
                host_vars = source.read_dict_attr("vars")

                self.update(groups=groups, host_vars=host_vars)
            elif source.type() == "ansible_host_var":
                host_vars = {source.read_attr(
                    "key"): source.read_attr("value")}

                self.update(host_vars=host_vars)
        self.groups = sorted(self.groups)

    def get_vars(self):
        '''Get the host's variable dictionary.'''
        return dict(self.host_vars)


class AnsibleGroup(object):
    '''
    AnsibleGroup represents a group for the Ansible inventory.
    '''

    def __init__(self, groupname, source=None):
        self.groupname = groupname
        self.sources = []
        self.hosts = set()
        self.children = set()
        self.group_vars = {}

        if source:
            self.add_source(source)

    def update(self, children=None, hosts=None, group_vars=None):
        '''
        Update host resource with additional children, hosts, or group variables.
        '''
        if hosts:
            self.hosts.update(hosts)
        if children:
            self.children.update(children)
        if group_vars:
            self.group_vars.update(group_vars)

    def add_source(self, source):
        '''Add a Terraform resource to the sources list.'''
        self.sources.append(source)

    def build(self):
        '''Assemble group details from registered sources.'''
        self.sources.sort(key=lambda source: source.priority())
        for source in self.sources:
            if source.type() == "ansible_group":
                children = source.read_list_attr("children")
                group_vars = source.read_dict_attr("vars")

                self.update(children=children, group_vars=group_vars)
            elif source.type() == "ansible_group_var":
                group_vars = {source.read_attr(
                    "key"): source.read_attr("value")}

                self.update(group_vars=group_vars)

        self.hosts = sorted(self.hosts)
        self.children = sorted(self.children)

    def to_dict(self):
        '''Prepare structure for final Ansible inventory JSON.'''
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
