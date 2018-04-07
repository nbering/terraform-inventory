variable "hostnames" {
  type = "list"

  default = [
    "broad-union",
    "young-violet",
    "lively-tree",
    "mute-fog",
    "rough-bread",
  ]
}

variable "domain" {
  default = "example.com"
}

resource "ansible_host" "count_advanced" {
  count              = "${length(var.hostnames)}"
  inventory_hostname = "${element(var.hostnames, count.index)}.${var.domain}"
}
