data "aws_subnet" "private" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}
resource "terraform_data" "topology" {
  lifecycle {
    precondition {
      condition     = length(toset([for s in data.aws_subnet.private : s.availability_zone])) == 3
      error_message = "Subnets must span three Availability Zones."
    }
    precondition {
      condition     = alltrue([for s in data.aws_subnet.private : s.vpc_id == var.vpc_id && !s.map_public_ip_on_launch])
      error_message = "Subnets must belong to the selected VPC and disable public IP assignment; separately verify private routing."
    }
  }
}
