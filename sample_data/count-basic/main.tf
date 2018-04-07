resource "ansible_host" "count_sample" {
  count              = 5
  inventory_hostname = "count-sample-${count.index}.example.com"
}
