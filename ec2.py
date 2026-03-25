import os
import subprocess
from botocore.exceptions import ClientError, WaiterError

def get_user_data_script():
    return """#!/bin/bash
    dnf update
    dnf upgrade -y
    dnf install -y httpd
    systemctl enable httpd
    systemctl start httpd
    """

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
    **DEPRECATED!** => USE create_security_group()

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

def create_security_group(ec2_client):
    """

    Boto3 documentation for 'Working with SGs in Amazon EC2'
    https://docs.aws.amazon.com/boto3/latest/guide/ec2-example-security-group.html

    Boto3 documentation for EC2.Client.describe_security_groups(**kwargs)
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_groups.html

    Boto3 documentation for EC2.Client.authorize_security_group_ingress(**kwargs)
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/authorize_security_group_ingress.html

    Boto3 documentation for EC2 Resource handle security_groups
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/service-resource/security_groups.html

    :param ec2_client:
    :return:
    """
    vpc_id = get_default_vpc_id(ec2_client)

    try:
        # # Need to make sure it doesn't already exist for testing or error
        # security_groups = list(ec2_resource.security_groups.filter(
        #     Filters=[
        #         {'Name': 'group-name',
        #          'Values': ['EC2_public_access']},
        #     ]
        # ))
        #
        # if security_groups:
        #     return security_groups[0].id

        existing_security_groups = ec2_client.describe_security_groups(GroupNames=[
            'EC2_public_access',
        ],)
        # Response dict | first entry in list of security groups | Group Name
        if existing_security_groups['SecurityGroups'][0]['GroupName'] == 'EC2_public_access':
            return existing_security_groups['SecurityGroups'][0]['GroupId'] # not GroupName (Error:)
    except ClientError: # EC2 throws an error here instead of an empty list if it doesn't exsits
        response = ec2_client.create_security_group(GroupName='EC2_public_access',
                                                    Description='Joe OMahony ACS Assignment01)', # No apostrophe for O'Mahony
                                                    VpcId=vpc_id)

        security_group_id = response['GroupId']

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': 80,
                 'ToPort': 80,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                 'FromPort': 443,
                 'ToPort': 443,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', # SSH
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ],
        )
    return security_group_id

def delete_security_group(ec2_client, group_name):
    """

    Can't have dependent objects for deletion
https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/delete_security_group.html
    :param group_name:
    :param ec2_client:
    :return:
    """
    try:
        response = ec2_client.delete_security_group(GroupName=group_name)
        return response # Response Syntax {'Return': True|False,'GroupId': 'string'}

    except ClientError as err:
        return err
    except Exception as err:
        return err


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
    # default_subnet_id = get_subnet_id_default_vpc(ec2_client)
    # default_security_group_id = get_security_group_id_default_vpc(ec2_client)
    instance = ec2_resource.create_instances(
        ImageId='ami-0f3caa1cf4417e51b', # latest Amazon Linux LTS AMI
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.nano',
        SecurityGroupIds=[
            create_security_group(ec2_client),
        ],
        # SubnetId=default_subnet_id,
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
    try:
        waiter.wait(
            InstanceIds=[
                created_instance_id,
            ],
            # WaiterConfig={ # 'A dictionary that provides parameters to control waiting behavior.'
            #     'Delay': 30, # seconds, 15 default
            #     'MaxAttempts': 20 # default 40
            # },
        )
    except WaiterError:
        """
        botocore.exceptions.WaiterError: Waiter InstanceRunning failed: Waiter encountered a terminal failure state: For expression "Reservations[].Instances[].State.Name" we matched expected path: "shutting-down" at least once
"""
        return created_instance_id

    return created_instance_id

def terminate_instances(ec2_resource, ec2_client, instance_ids):
    """
    Function that takes a list of EC2 instance IDs and terminates them.

    instance terminated waiter
     https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/waiter/InstanceTerminated.html

    :param ec2_client:
    :param ec2_resource: EC2 Resource handle
    :param instance_ids: List of EC2 instance IDs
    :return: responses List of instance terminated responses
    """
    responses = []

    for instance_id in instance_ids:
        instance = ec2_resource.Instance(instance_id)
        termination_response = instance.terminate()
        responses.append(termination_response)

    # Adding a waiter to avoid:
    # An error occurred (DependencyViolation) when calling the DeleteSecurityGroup operation
    # waiter.wait(
    #     InstanceIds=[
    #         'string',
    waiter = ec2_client.get_waiter('instance_terminated')
    waiter.wait(
        InstanceIds=instance_ids,
    )

    return responses

def get_all_instances_str(ec2_resource):
    """
    Function that returns a list of all EC2 instance details

    Boto3 documentation for Resource handle EC2 instances
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/service-resource/instances.html

    Boto3 documentation for EC2 instance states
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/instance/state.html

    :param ec2_resource: EC2 Resource handle
    :return: List of Dictionary EC2 instance details
    """
    pending_instances = []
    running_instances = []
    shutting_down_instances = []
    terminated_instances = []
    stopping_instances = []
    stopped_instances = []

    for instance in ec2_resource.instances.all():  # returns a list(ec2.instance)
        if instance.state['Name'] == 'pending':
            pending_instances.append(instance.instance_id)
        elif instance.state['Name'] == 'running':
            running_instances.append(instance.instance_id)
        elif instance.state['Name'] == 'shutting-down':
            shutting_down_instances.append(instance.instance_id)
        elif instance.state['Name'] == 'terminated':
            terminated_instances.append(instance.instance_id)
        elif instance.state['Name'] == 'stopping':
            stopping_instances.append(instance.instance_id)
        else:
            stopped_instances.append(instance.instance_id) # stopped

    instance_string = "All EC2 Instances:\n"

    if len(pending_instances) > 0:
        instance_string += f"\t{len(pending_instances)} pending EC2 instance(s) =>  " + str(pending_instances) + "\n"
    if len(running_instances) > 0:
        instance_string += f"\t{len(running_instances)} running EC2 instance(s) => " + str(running_instances) + "\n"
    if len(shutting_down_instances) > 0:
        instance_string += f"\t{len(shutting_down_instances)} shutting down EC2 instance(s) => " + str(shutting_down_instances) + "\n"
    if len(terminated_instances) > 0:
        instance_string += f"\t{len(terminated_instances)} terminated EC2 instance(s) => " + str(terminated_instances) + "\n"
    if len(stopping_instances) > 0:
        instance_string += f"\t{len(stopping_instances)} stopping EC2 instance(s) => " + str(stopping_instances) + "\n"
    if len(stopped_instances) > 0:
        instance_string += f"\t{len(stopped_instances)} stopped EC2 instance(s) => " + str(stopped_instances)

    return instance_string


def get_unterminated_instances(ec2_resource):
    """
    Function that returns a list of all unterminated EC2 instance IDs

    :param ec2_resource: EC2 Resource handle
    :return: instances List of unterminated EC2 instance IDs
    """
    instances = []

    for instance in ec2_resource.instances.all():
        if instance.state['Name'] != 'terminated':
            instances.append(instance.instance_id)

    return instances

def get_instance_availability_zone(ec2_resource, instance_id):
    # https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/instance/placement.html
    instance = ec2_resource.Instance(instance_id)
    availability_zone = instance.placement['AvailabilityZone']
    return availability_zone

def create_index_document(ec2_instance_id, ec2_instance_availability_zone, s3_object_details):
    if os.path.exists("index.html"): # since hard-coded, need to existence check
        os.remove("index.html")

    # reference for EC2 Obj bucket URL https://stackoverflow.com/questions/48608570/python-3-boto-3-aws-s3-get-object-url
    ec2_html_script = f"""
    <html>
    <head>
    <title>JOMahony A01</title>
    </head>
    <body>
    <h1>Joe O'Mahony ACS A01</h1>
    <hr />
    <h2>EC2 Server Details</h2>
    <ul>
    <li><b>Instance ID:</b> {ec2_instance_id}</li>
    <li><b>Server availability zone:</b> {ec2_instance_availability_zone}</li>
    </ul>
    <img src="https://{s3_object_details['BucketName']}.s3.amazonaws.com/{s3_object_details['ObjKey']}">
    </body>
    </html>
    """

    # https://docs.python.org/3/library/functions.html#open
    with open("index.html", "w") as file:  # just with open and args
        file.write(ec2_html_script)

def delete_index_document():
    # https://docs.python.org/3/library/os.html#os.remove
    os.remove("index.html")

def check_httpd_active(instance):
    result = subprocess.run([
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        "JOMahony_A01_RSA.pem",
        f"ec2-user@{instance.public_ip_address}",
        "service httpd status"
    ], text=True, capture_output=True)

    # https://docs.python.org/3/library/functions.html
    # "Active: active (running)" shows when actually running alongside PID, etc.
    if result.stdout.find("Active: active (running)") > 0: # -1 == not found
        return True

    return False

def transfer_index_to_ec2(instance):
    # https://docs.python.org/3/library/subprocess.html
    # StrictHostKeyChecking=no is a workaround, without it the connection is refused.
    # In the CLI, you need to confirm whether or not to add the host key on first connection, but I couldn't just run
    # another subprocess with a 'yes' argument and continue on.
    subprocess.run([
        "scp",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        "JOMahony_A01_RSA.pem",
        "index.html",
        f"ec2-user@{instance.public_ip_address}:"
    ], check=True)  # Silent fail without, continues on

    subprocess.run([
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        "JOMahony_A01_RSA.pem",
        f"ec2-user@{instance.public_ip_address}",
        "sudo mv ~/index.html /var/www/html/index.html"
    ], check=True)
