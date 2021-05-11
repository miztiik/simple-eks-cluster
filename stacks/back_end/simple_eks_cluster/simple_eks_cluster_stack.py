from aws_cdk import aws_iam as _iam
from aws_cdk import aws_eks as _eks
from aws_cdk import aws_ec2 as _ec2
from aws_cdk import core as cdk
from stacks.miztiik_global_args import GlobalArgs


class SimpleEksClusterStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level,
        vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create EKS Cluster Role
        # https://docs.aws.amazon.com/eks/latest/userguide/getting-started-console.html

        self._eks_cluster_svc_role = _iam.Role(
            self,
            "c_SvcRole",
            assumed_by=_iam.ServicePrincipal(
                "eks.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKSClusterPolicy"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKS_CNI_Policy"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKSVPCResourceController"
                )
            ]
        )


        self._eks_node_role = _iam.Role(
            self,
            "c_NodeRole",
            assumed_by=_iam.ServicePrincipal(
                "ec2.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKSWorkerNodePolicy"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKS_CNI_Policy"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                )
            ]
        )

        c_admin_role = _iam.Role(
            self,
            "c_AdminRole",
            assumed_by=_iam.CompositePrincipal(
                _iam.AccountRootPrincipal(),
                _iam.ServicePrincipal(
                    "ec2.amazonaws.com")
            )
        )
        c_admin_role.add_to_policy(
            _iam.PolicyStatement(
                effect=_iam.Effect.ALLOW,
                actions=[
                    "eks:DescribeCluster"
                ],
                resources=["*"]
            )
        )

        # Create Security Group for EKS Cluster SG
        self.eks_cluster_sg = _ec2.SecurityGroup(
            self,
            "eksClusterSG",
            vpc=vpc,
            description="EKS Cluster security group",
            allow_all_outbound=True,
        )
        cdk.Tags.of(self.eks_cluster_sg).add("Name", "eks_cluster_sg")

        # https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html
        self.eks_cluster_sg.add_ingress_rule(
            peer=self.eks_cluster_sg,
            connection=_ec2.Port.all_traffic(),
            description="Allow incoming within SG"
        )

        clust_name = "1_cdk_c"

        eks_c_admin = _iam.Role(
            self,
            f"admin_{clust_name}",
            assumed_by=_iam.AccountRootPrincipal(),
            role_name="c_admin"
        )

        eks_cluster_1 = _eks.Cluster(
            self,
            f"c_{clust_name}",
            cluster_name=f"{clust_name}",
            version=_eks.KubernetesVersion.V1_18,
            vpc=vpc,
            vpc_subnets=[
                _ec2.SubnetSelection(
                    subnet_type=_ec2.SubnetType.PUBLIC),
                _ec2.SubnetSelection(
                    subnet_type=_ec2.SubnetType.PRIVATE)
            ],
            default_capacity=0,
            masters_role=c_admin_role,
            role=self._eks_cluster_svc_role,
            security_group=self.eks_cluster_sg,
            endpoint_access=_eks.EndpointAccess.PUBLIC
            # endpoint_access=_eks.EndpointAccess.PUBLIC_AND_PRIVATE
        )

        node_grp_1 = eks_cluster_1.add_nodegroup_capacity(
            f"n_g_{clust_name}",
            nodegroup_name=f"{clust_name}_n_g",
            instance_types=[
                _ec2.InstanceType("t3.medium"),
                _ec2.InstanceType("t3.large"),
            ],
            disk_size=20,
            min_size=1,
            max_size=6,
            desired_size=2,
            labels={"app": "miztiik_ng", "lifecycle": "on_demand"},
            subnets=_ec2.SubnetSelection(
                subnet_type=_ec2.SubnetType.PUBLIC),
            ami_type=_eks.NodegroupAmiType.AL2_X86_64,
            # remote_access=_eks.NodegroupRemoteAccess(ssh_key_name="eks-ssh-keypair"),
            capacity_type=_eks.CapacityType.ON_DEMAND,
            node_role=self._eks_node_role
        )

        # This code block will provision worker nodes with launch configuration
        """
        fargate_n_g_3 = eks_cluster_1.add_fargate_profile(
            "FargateEnabled",
            fargate_profile_name="miztiik_n_g_fargate",
            selectors=[
                _eks.Selector(
                    namespace="miztiik_ns",
                    labels={"fargate": "enabled"}
                )
            ]
        )
        """

        """
        # This code block will provision worker nodes with launch configuration
        node_grp_2 =  eks_cluster.add_auto_scaling_group_capacity('spot-asg-az-a',
                                                    auto_scaling_group_name=prj_name + env_name + '-spot-az-a',
                                                    min_capacity=1,
                                                    max_capacity=1,
                                                    desired_capacity=1,
                                                    key_name=f"{key}",
                                                    instance_type=ec2.InstanceType(
                                                        't3.small'),
                                                    vpc_subnets=ec2.SubnetSelection(
                                                        availability_zones=["ap-southeast-1a"], subnet_type=ec2.SubnetType.PRIVATE),
                                                    bootstrap_options={
                                                        "kubelet_extra_args": "--node-labels=node.kubernetes.io/lifecycle=spot,daemonset=active,app=general --eviction-hard imagefs.available<15% --feature-gates=CSINodeInfo=true,CSIDriverRegistry=true,CSIBlockVolume=true,ExpandCSIVolumes=true"
                                                    }
                                                    )
        """

        """
        # Install Metrics Server
        eks_cluster_1.add_helm_chart(
            f"metrics_{clust_name}",
                chart = 'metrics-server',
                repository = "https://charts.helm.sh/stable",
                namespace = "toolstools
            )
        """

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )
        """
        output_1 = cdk.CfnOutput(
            self,
            "eksClusterRole",
            value=f"{self._eks_cluster_svc_role.role_name}",
            description="EKS Cluster Service Role"
        )

        output_2 = cdk.CfnOutput(
            self,
            "OIDSEndpointUrl",
            value=f"{_cluster.cluster_open_id_connect_issuer_url}",
            description="EKS Cluster OIDS Endpoint Url"
        )
        output_3 = cdk.CfnOutput(
            self,
            "OIDSEndpoint",
            value=f"{_cluster.cluster_open_id_connect_issuer}",
            description="EKS Cluster OIDS Endpoint"
        )
        """
