terraform {
  required_version = "~> 0.11.0"
}

provider "ansible" {
  version = "~> 0.0.6"
}

resource "ansible_host" "www" {
  inventory_hostname = "www.example.com"
  groups             = ["example", "web"]

  vars = {
    foo = "aaa"
    bar = "bbb"
  }
}

resource "ansible_host" "db" {
  inventory_hostname = "db.example.com"
  groups             = ["example", "db"]

  vars = {
    foo = "ccc"
    bar = "ddd"
  }
}

resource "ansible_host_var" "extra" {
  inventory_hostname = "www.example.com"
  key                = "db_host"
  value              = "${ansible_host.db.inventory_hostname}"
}

resource "ansible_host_var" "override" {
  inventory_hostname = "www.example.com"
  key                = "foo"
  value              = "eee"
}

resource "ansible_host_var" "underride" {
  inventory_hostname = "www.example.com"
  variable_priority  = 10
  key                = "bar"
  value              = "ggg"
}

resource "ansible_group" "web" {
  inventory_group_name = "web"
  children             = ["foo", "bar", "baz"]

  vars = {
    foo = "bar"
    bar = 2
  }
}

resource "ansible_group_var" "override" {
  inventory_group_name = "web"
  key                  = "foo"
  value                = "fff"
}

resource "ansible_group_var" "underride" {
  inventory_group_name = "web"
  variable_priority    = 10
  key                  = "bar"
  value                = "hhh"
}

resource "ansible_group_var" "extra" {
  inventory_group_name = "db"
  key                  = "ansible_user"
  value                = "postgres"
}
