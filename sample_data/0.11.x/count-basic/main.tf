terraform {
  required_version = "~> 0.11.0"
}

provider "ansible" {
  version = "~> 0.0.5"
}

resource "ansible_host" "count_sample" {
  count              = 5
  inventory_hostname = "count-sample-${count.index}.example.com"
}
