def get_default_vpc_id(ec2_client):
    """
    Function to return the ID of the default VPC.

    - Takes the EC2 client handle as a parameter.
    - Uses the describe_vpcs() method with a filter to get a dictionary of default VPCs.
    - Takes the first entry in the list of default VPCs and gets its corresponding VPC ID.
    - Returns the ID of the default VPC.

    Boto3 documentation link:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_vpcs.html

    :param ec2_client: EC2 client handle
    :return: default_vpc_id The default VPC ID
    """
    default_vpc = ec2_client.describe_vpcs(
    Filters=[
        {
            'Name': 'is-default',
            'Values': [
                'true',
            ]
        },
    ],
    )
    # Default VPCs [dict] | VPC entry 0 [list] | VpcId (string) [dict]
    default_vpc_id = default_vpc['Vpcs'][0]['VpcId']
    return default_vpc_id

def get_subnet_id_default_vpc(ec2_client):
    """
    Function to return the subnet ID of the default VPC.

    - Takes the EC2 client handle as an argument.
    - Calls get_default_vpc_id() to get the default VPC ID for subnet filtering.
    - Calls describe_subnets() with the default VPC ID as a filter to get a dictionary of subnets within that VPC.
    - Accesses the dictionary of subnets associated with default VPC and returns the subnet ID of the first subnet.

    Boto3 documentation link:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_subnets.html

    :param ec2_client: EC2 client handle
    :return: subnet_id The subnet ID associated with the default VPC
    """
    default_vpc_id =  get_default_vpc_id(ec2_client)
    subnets = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                   default_vpc_id,
                ]
            },
        ],
    )
    # Default subnets [dict] | subnet 0 [list] | SubnetId: [dict]
    subnet_id = subnets['Subnets'][0]['SubnetId']
    return subnet_id

def get_security_group_id_default_vpc(ec2_client):
    """
    Function to return the ID of the default security group associated with the default VPC.

    - Takes the EC2 client handle as an argument.
    - Calls get_default_vpc_id() to get the default VPC ID for security group filtering.
    - Filters describe_security_groups() with the default VPC ID and default flag.
    - Returns the ID of the first default security group.

    Boto3 documentation link:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_groups.html

    :param ec2_client: EC2 client handle
    :return: security_group_id The default security group ID of the default VPC
    """
    default_vpc_id = get_default_vpc_id(ec2_client)
    security_groups = ec2_client.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [default_vpc_id],
            },
            {
                'Name': 'group-name',
                'Values': ['default']
            }
        ]
    )
    # Security groups [dict] | security group 0 [list] | security group ID [dict]
    security_group_id = security_groups['SecurityGroups'][0]['GroupId']
    return security_group_id

def create_instance(ec2_resource, ec2_client, key_name, user_data=''):
    """
    Function that creates an EC2 instance and returns the instance ID when that instance is running.

    - Takes both the EC2 client and resource handles as arguments.
    - Gets the default subnet ID from the default VPC.
    - Gets the default security group ID from the default VPC.
    - Calls ec2_resource.create_instances() with the function arguments and subnet/security group ID
      to create an instance.
    - Instantiates an 'instance_running' waiter and waits until the EC2 instance's status
      is changed to 'running' (minimum wait of 30 seconds).
    - Returns the ID of the created, running instance.

    Boto3 documentation for ec2_resource.create_instances()
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/service-resource/create_instances.html

    Boto3 documentation for the ec2_client.get_waiter() method
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/get_waiter.html

    Boto3 documentation for all EC2 waiter_names
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2.html#waiters

    Boto3 documentation for the 'Instance Running' waiter_name for ec2_client.get_waiter()
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/waiter/InstanceRunning.html


    :param ec2_resource: EC2 Resource handle
    :param ec2_client: EC2 Client handle
    :param key_name: RSA key name
    :param user_data: Bash script to pass to the EC2
    :return: created_instance_id EC2 instance ID
    """
    default_subnet_id = get_subnet_id_default_vpc(ec2_client)
    default_security_group_id = get_security_group_id_default_vpc(ec2_client)
    instance = ec2_resource.create_instances(
        ImageId='ami-0f3caa1cf4417e51b', # latest Amazon Linux LTS AMI
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.nano',
        SecurityGroupIds=[
            default_security_group_id,
        ],
        SubnetId=default_subnet_id,
        UserData=user_data,
        KeyName=key_name,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'CreatedBy', 'Value': 'JoeOMahony'},
                    {'Key': 'Module', 'Value': 'AutomatedCloudServices'},
                    {'Key': 'Assignment', 'Value': 'Assignment01'}
                ]
            }
        ],
    )

    # Returns list of instance objects
    created_instance_id = instance[0].instance_id
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(
        InstanceIds=[
                created_instance_id,
        ],
        # WaiterConfig={ # "A dictionary that provides parameters to control waiting behavior.'
        #     'Delay': 30, # seconds, 15 default
        #     'MaxAttempts': 20 # default 40
        # },
    )

    return created_instance_id

# NetworkInterfaces=[
#             {
#                 'AssociatePublicIpAddress': True | False,
#             }
#         ]

def get_all_instances(ec2_resource):
    instances = []

    for instance in ec2_resource.instances.all():
        instances.append(instance)

    return instances
