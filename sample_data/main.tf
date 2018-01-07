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
