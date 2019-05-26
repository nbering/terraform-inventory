terraform {
  required_version = "~> 0.12.0"
}

provider "ansible" {
  version = "~> 1.0.1"
}

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
