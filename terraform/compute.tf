locals {
  system_node_groups = {
    for subnet in data.aws_subnet.private : "system-${subnet.availability_zone}" => {
      capacity_type  = "ON_DEMAND"
      subnet_ids     = [subnet.id]
      instance_types = var.system_instance_types
      min_size       = var.system_node_capacity.min / 3
      desired_size   = var.system_node_capacity.desired / 3
      max_size       = var.system_node_capacity.max / 3
      labels         = { "workload.example.com/pool" = "system" }
      taints = {
        critical = { key = "CriticalAddonsOnly", value = "true", effect = "NO_SCHEDULE" }
      }
    }
  }
}
