# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Respect `variable_priority`, added in providers releases [0.0.6](https://github.com/nbering/terraform-provider-ansible/releases/tag/v0.0.6)/[1.0.2](https://github.com/nbering/terraform-provider-ansible/releases/tag/v1.0.2)

### Changed
- List values in output are now sorted for consistency, and to make regression testing easier
- With state files where `variable_priority` is not set, the default values of 50 (for `ansible_host` and `ansible_group`) and 60 (for `ansible_host_var` and `ansible_group_var`) will be inferred, changing variable merging behaviour

## [2.1.0] - 2019-05-20
### Added
- Support for `ansible_host_var` resource type
- Support for `ansible_group_var` resource type

### Fixed
- Corrected a minor issue where `ansible_host` or `ansible_host_var` resources with the same `inventory_hostname` would result in multiple copies of the hostname in any groups they shared in common (including the "all" group)

## [2.0.0] - 2019-05-05
### Added
- Support for Terraform 0.12's new state file structure
- Simple regression testing with Bash scripts

### Changed
- Removed version-specific python shebang, as `terraform.py` seems to work fine with Python 2.7 and 3.x

### Removed
- `terraform state pull` no longer uses `-input=false` as this argument is not recognized by Terraform 0.12

## [1.1.0] - 2019-01-09
### Added
- Support for Terraform workspaces via `ANSIBLE_TF_WS_NAME` environment variable. Thanks [@dnitsch]!

## [1.0.1] - 2018-02-25
### Added
- Support for `ansible_group` resource, added in [nbering/terraform-provider-ansible#8](https://github.com/nbering/terraform-provider-ansible/pull/8)

## [1.0.0] - 2018-01-07
### Added
- Added `ANSIBLE_TF_DIR` environment variable to set Terraform configuration directory.

### Changed
- Ported the script to Python to be more compatible with the Ansible ecosystem.
- Changed `TERRAFORM_PATH` environment variable to `ANSIBLE_TF_PATH`.

### Deprecated
- The earlier NodeJS implementation will not be supported going forward.

## [0.0.2] - 2018-01-06
### Changed
- Update docs and package info for move back to GitHub.

[Unreleased]: https://github.com/nbering/terraform-inventory/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/nbering/terraform-inventory/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/nbering/terraform-inventory/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/nbering/terraform-inventory/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/nbering/terraform-inventory/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/nbering/terraform-inventory/compare/v0.0.2...v1.0.0
[0.0.2]: https://github.com/nbering/terraform-inventory/compare/v0.0.1...v0.0.2

[@dnitsch]:https://github.com/dnitsch
