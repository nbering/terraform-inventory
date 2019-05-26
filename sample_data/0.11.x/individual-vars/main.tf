terraform {
  required_version = "~> 0.11.0"
}

provider "ansible" {
  version = "~> 0.0.5"
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

resource "ansible_group_var" "extra" {
  inventory_group_name = "db"
  key                  = "ansible_user"
  value                = "postgres"
}
