# Terraform Inventory

An Ansible [dynamic inventory][2] script to process Terraform state and return
Ansible host data from [Terraform Provider for Ansible][1] host resources. See the
Terraform Provider for it's own installation and use.

## Usage

Copy the [terraform.py](./terraform.py) script file to a location on your system. Ansible's own documentation suggests the location `/etc/ansible/terraform.py`, but the particular location does not matter to the script. Ensure it has executable permissions (`chmod +x /etc/ansible/terraform.py`).

With your Ansible playbook and Terraform configuration in the same directory, run Ansible with the `-i` flag to set the inventory source.

```
$ ansible-playbook -i /etc/ansible/terraform.py playbook.yml
```

## Environment Variables
### ANSIBLE\_TF\_BIN

Override the path to the Terraform command executable. This is useful if you have multiple copies or versions installed and need to specify a specific binary. The inventory script runs the `terraform state pull` command to fetch the Terraform state, so that remote state will be fetched seemlessly regardless of the backend configuration.

### ANSIBLE\_TF\_DIR

Set the working directory for the `terraform` command when the scripts shells out to it. This is useful if you keep your terraform and ansible configuration in separate directories. Defaults to using the current working directory.

## License

Licensed for use under the [MIT License](./LICENSE).

[1]: https://github.com/nbering/terraform-provider-ansible/
[2]: http://docs.ansible.com/ansible/latest/intro_dynamic_inventory.html
