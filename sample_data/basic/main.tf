resource "ansible_host" "www" {
    inventory_hostname = "www.example.com"
    groups             = ["example", "web"]
    vars {
        fooo = "aaa"
        bar  = "bbb"
    }
}

resource "ansible_host" "db" {
    inventory_hostname = "db.example.com"
    groups             = ["example", "db"]
    vars {
        fooo = "ccc"
        bar  = "ddd"
    }
}

resource "ansible_group" "web" {
    inventory_group_name = "web"
    children = ["foo", "bar", "baz"]
    vars {
        foo = "bar"
        bar = 2
    }
}

# A host with no optional properties.
resource "ansible_host" "base" {
    inventory_hostname = "base.example.com"
}

# A group with no optional properties.
resource "ansible_group" "base" {
    inventory_group_name = "base"
}
