module "karpenter" {
  source                          = "terraform-aws-modules/eks/aws//modules/karpenter"
  version                         = "21.3.1"
  cluster_name                    = module.eks.cluster_name
  namespace                       = "kube-system"
  service_account                 = "karpenter"
  create_pod_identity_association = true
  enable_spot_termination         = true
}
