variable "region" {
  type = string
}
variable "name" {
  type    = string
  default = "eks-migration-lab"
}
variable "kubernetes_version" {
  type        = string
  description = "Explicit EKS version selected after regional availability and support review."
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) == 3
    error_message = "Supply three different private subnet IDs."
  }
}
variable "operator_role_arn" {
  type        = string
  description = "Existing IAM role granted cluster administrator access."
}
variable "system_instance_types" {
  type    = list(string)
  default = ["m6i.large", "m6a.large"]
}
variable "vpc_cni_version" {
  type        = string
  description = "Pinned VPC CNI add-on version compatible with the selected EKS version."
}
variable "coredns_version" {
  type = string
}
variable "kube_proxy_version" {
  type = string
}
variable "pod_identity_agent_version" {
  type = string
}

variable "network_policy_enforcing_mode" {
  type        = string
  default     = "standard"
  description = "Use strict only after system and workload dependency policies have been installed and tested."
  validation {
    condition     = contains(["standard", "strict"], var.network_policy_enforcing_mode)
    error_message = "Mode must be standard or strict."
  }
}

variable "system_node_capacity" {
  type        = object({ min = number, desired = number, max = number })
  default     = { min = 3, desired = 3, max = 6 }
  description = "Total system node counts, split equally across three AZ-scoped managed node groups; each total must be divisible by three."
  validation {
    condition     = var.system_node_capacity.min >= 3 && var.system_node_capacity.min <= var.system_node_capacity.desired && var.system_node_capacity.desired <= var.system_node_capacity.max && alltrue([for n in [var.system_node_capacity.min, var.system_node_capacity.desired, var.system_node_capacity.max] : floor(n) == n && n % 3 == 0])
    error_message = "System totals must be multiples of three with 3 <= min <= desired <= max."
  }
}

variable "cost_budget" {
  type        = object({ monthly_limit_usd = number, sns_topic_arn = string })
  default     = null
  description = "Optional total-account monthly budget and existing authorized SNS topic; disabled until explicitly supplied."
  validation {
    condition     = var.cost_budget == null ? true : var.cost_budget.monthly_limit_usd > 0 && can(regex("^arn:[^:]+:sns:[^:]+:[0-9]{12}:.+$", var.cost_budget.sns_topic_arn))
    error_message = "Supply a positive monthly USD limit and an existing SNS topic ARN, or leave cost_budget null."
  }
}
