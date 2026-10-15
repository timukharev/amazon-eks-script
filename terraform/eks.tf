module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.3.1"

  name                                     = var.name
  kubernetes_version                       = var.kubernetes_version
  vpc_id                                   = var.vpc_id
  subnet_ids                               = var.private_subnet_ids
  endpoint_private_access                  = true
  endpoint_public_access                   = false
  enable_cluster_creator_admin_permissions = false
  access_entries = {
    operator = {
      principal_arn = var.operator_role_arn
      policy_associations = {
        administrator = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }
  addons = {
    vpc-cni = {
      addon_version  = var.vpc_cni_version
      before_compute = true
      configuration_values = jsonencode({
        enableNetworkPolicy = "true"
        env                 = { NETWORK_POLICY_ENFORCING_MODE = var.network_policy_enforcing_mode }
      })
    }
    coredns = {
      addon_version        = var.coredns_version
      configuration_values = jsonencode({ nodeSelector = { "workload.example.com/pool" = "system" } })
    }
    kube-proxy             = { addon_version = var.kube_proxy_version }
    eks-pod-identity-agent = { addon_version = var.pod_identity_agent_version, before_compute = true }
  }
  eks_managed_node_groups  = local.system_node_groups
  node_security_group_tags = { "karpenter.sh/discovery" = var.name }
  depends_on               = [terraform_data.topology]
}
