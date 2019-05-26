terraform {
  required_version = "~> 0.12.0"
}

provider "ansible" {
  version = "~> 1.0.1"
}

resource "ansible_host" "count_sample" {
  count              = 5
  inventory_hostname = "count-sample-${count.index}.example.com"
}
