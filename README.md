# Terraform Inventory

An Ansible dynamic inventory script to process Terraform state and return
Ansible host data from [Terraform Provider for Ansible][1] host resources. See the
Terraform Provider for it's own installation and use.

## Installation and Use

### Global
```
$ npm install -g @nbering/terraform-inventory

$ ansible-playbook -i $(which terraform-inventory) playbook.yml
```

### Local
```
$ npm install @nbering/terraform-inventory

$ ansible-playbook -i node_modules/.bin/terraform-inventory playbook.yml
```

> This script shells out to `terraform state pull` from the current working
directory. This allows it to support Terraform Remote State, but generally
restricts use to wherever you run terraform from.

## Ansible Version

Tested with the following ansible versions:
- v2.3.1.0-0.1.rc1
- v2.4.1.0-1

Should support Ansible greater than v1.3.

## Terraform State Versions

Tested with a range of versions from v0.9.11 to v0.11.0.

> Warning: Terraform does not consider the statefile contents to be a public
interface. Future versions of Terraform may break support for the application
without indicating a breaking change in the version number, migration guide, or
changelog.

## License

Licensed for use under the [MIT License](./LICENSE).

[1]: https://gitlab.com/nbering/ansible-provider-terraform/
