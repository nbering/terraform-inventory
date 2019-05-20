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

resource "ansible_group_var" "extra" {
  inventory_group_name = "db"
  key                  = "ansible_user"
  value                = "postgres"
}
