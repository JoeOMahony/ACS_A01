import os
import subprocess
import time

from botocore.exceptions import ClientError, WaiterError

def get_user_data_script():
    """
    Returns a bash script to be used as user data when creating EC2 instances.

    - Uses the DNF package manager.
    - Updates, upgrades, then installs the httpd server.
    - Enables and starts the httpd service.

    :return: Bash script for updating, upgrading, and installing Apache server on Linux distros.
    """
    return """#!/bin/bash
    dnf update -y
    dnf upgrade -y
    dnf install -y httpd
    systemctl enable httpd
    systemctl start httpd
    """

def get_default_vpc_id(ec2_client):
    """
    Returns the ID of the default VPC.

    - Uses the describe_vpcs() method with a filter to get a dictionary of default VPCs.
    - Takes the first entry in the list of default VPCs, gets, and returns its corresponding VPC ID.

    Boto3 documentation for ec2_client.describe_vpcs() link:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_vpcs.html

    :param ec2_client: EC2 client handle
    :return: The ID of the default VPC
    """
    try:
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
    except IndexError as index_err:
        print(f'There is no default VPC on your account. You must have a default VPC on your account to use this program. Error: {index_err}')
    except ClientError as client_err:
        print(f'Error in getting default VPC ID, check AWS permissions. Error: {client_err}')
        raise # no default_vpc_id means no security group created, so major

def create_security_group(ec2_client):
    """
    Creates a new security group allowing public HTTP/HTTPS/SSH access called EC2_public_access.

    - Checks if the EC2_public_access security group already exists.
    - If it does already exist, returns its ID.
    - If it doesn't, a new security group is created.

    Reference -> Boto3 documentation for 'Working with SGs in Amazon EC2':
    https://docs.aws.amazon.com/boto3/latest/guide/ec2-example-security-group.html

    Boto3 documentation for EC2.Client.describe_security_groups(**kwargs):
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_groups.html

    Boto3 documentation for EC2.Client.authorize_security_group_ingress(**kwargs):
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/authorize_security_group_ingress.html

    Boto3 documentation for EC2 Resource handle security_groups:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/service-resource/security_groups.html

    :param ec2_client: EC2 client handle
    :return: ID of the created security group
    """
    vpc_id = get_default_vpc_id(ec2_client)
    try:
        # Need to make sure it doesn't already exist for testing or error
        existing_security_groups = ec2_client.describe_security_groups(GroupNames=[
            'EC2_public_access',
        ],)
        # Response dict | first entry in list of security groups | Group Name
        if existing_security_groups['SecurityGroups'][0]['GroupName'] == 'EC2_public_access':
            return existing_security_groups['SecurityGroups'][0]['GroupId'] # not GroupName (Error:)
    except ClientError: # EC2 throws an error here instead of an empty list if it doesn't exist.
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

        return security_group_id # Moved - Local variable 'security_group_id' might be referenced before assignment
    except Exception as err:
        # Because the above relies on the ClientError thrown due to AWS, this is really the only error handling going on
        # I've tried to refactor, but always end up going back to ClientError.
        raise Exception(f'Error occurred while creating the security group: {err}')

def delete_security_group(ec2_client, group_name):
    """
    Deletes the security group passed as argument.

    AWS requires all dependent resources to be removed before a security group can be deleted.
    From this, EC2 instances must be in the 'Terminated' state. See the documentation linked below.

    Boto3 documentation for ec2_client.delete_security_group():
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/delete_security_group.html

    :param group_name: Name of the security group to be deleted
    :param ec2_client: EC2 client handle
    :return: None if successful, ClientError if unsuccessful due to existing dependencies on that security group
    """
    try:
        response = ec2_client.delete_security_group(GroupName=group_name)
        return response # Response Syntax {'Return': True|False,'GroupId': 'string'}
    except ClientError as client_err:
        print(f'A client error occurred when deleting the security group, check if the SG still has dependent resources: {client_err}')
        return False


def create_instance(ec2_resource, ec2_client, key_name, user_data=''):
    """
    Creates an EC2 instance and returns the instance ID when in the 'running' state.

    Function:

    - Depends on the region set in the argument client and resource handles.
    - Creates a new security group with public access for HTTP/HTTPS/SSH.
    - Creates a new T2.Nano instance using the latest Amazon Linux LTS release with the argument pem key and user data.
    - Instantiates an 'instance_running' waiter and waits until the EC2 instance's status
      is changed to 'running' (minimum wait of 30 seconds).
    - Returns the ID of the created, running instance.

    Boto3 documentation for ec2_resource.create_instances():
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/service-resource/create_instances.html

    Boto3 documentation for the ec2_client.get_waiter() method:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/get_waiter.html

    Boto3 documentation for all EC2 waiter_names:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2.html#waiters

    Boto3 documentation for the 'Instance Running' waiter_name for ec2_client.get_waiter():
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/waiter/InstanceRunning.html

    :param ec2_resource: EC2 Resource handle
    :param ec2_client: EC2 Client handle
    :param key_name: RSA key name
    :param user_data: Bash script to pass to the EC2
    :return: created_instance_id EC2 instance ID
    """
    try:
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
    except ClientError as client_err:
        print(f'A client error occurred when creating an EC2 instance, check your permissions. Error: {client_err}')
        raise # major

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
    except WaiterError as waiter_err:
        # botocore.exceptions.WaiterError: ...we matched expected path: "shutting-down" at least once
        print(f'An error occurred when waiting for the EC2 instance to come online, additional 30 second wait beginning. Error: {waiter_err}')
        time.sleep(30)

    return created_instance_id

def terminate_instances(ec2_resource, ec2_client, instance_ids):
    """
    Takes a list of EC2 instance IDs and terminates them.

    Boto3 documentation for instance terminated waiter:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/waiter/InstanceTerminated.html

    :param ec2_client: EC2 client handle
    :param ec2_resource: EC2 Resource handle
    :param instance_ids: List of EC2 instance IDs to be terminated
    :return: responses List of instance terminated responses
    """
    responses = []

    try:
        for instance_id in instance_ids:
            instance = ec2_resource.Instance(instance_id)
            termination_response = instance.terminate()
            responses.append(termination_response)
    except ClientError as client_err:
        print(f'Client error when terminating EC2 instances, check there are instances running and you have permission to delete them. Error: {client_err}')
        return responses # return here so no need to attempt the waiter with an extra 30 seconds
    # Adding a waiter to avoid:
    # An error occurred (DependencyViolation) when calling the DeleteSecurityGroup operation
    # waiter.wait(InstanceIds=['string',
    try:
        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(
            InstanceIds=instance_ids,
        )
    except WaiterError as waiter_err:
        print(f'An error occurred when waiting for the EC2 instance to terminate, additional 30 second wait beginning. Error: {waiter_err}')
        time.sleep(30)

    return responses

def get_instance_availability_zone(ec2_resource, instance_id):
    """
    Returns the availability zone for the argument EC2 instance.

    Boto3 documentation for placement attributes of EC2 instance resources:
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/instance/placement.html

    :param ec2_resource: EC2 resource handle
    :param instance_id: EC2 instance ID to find the availability zone for
    :return:Availability zone of the argument EC2 instance
    """
    try:
        instance = ec2_resource.Instance(instance_id)
        availability_zone = instance.placement['AvailabilityZone']
        return availability_zone
    except ClientError as client_err:
        # not possible that the instance isn't running as creating an instance includes a waiter with error handling
        print(f'Error in getting the availability zone of your instance: {client_err}')
        raise

def create_index_document(ec2_instance_id, ec2_instance_availability_zone, s3_object_details):
    """
    Creates a local index.html document showing my name, the EC2 instance ID, and availability zone, with the
    argument S3 object displayed as an image.

    A note on os module error handling from the documentation:
    "All functions in this module raise OSError (or subclasses thereof) in the case of invalid or inaccessible
    file names and paths, or other arguments that have the correct type, but are not accepted by the operating system."
    https://docs.python.org/3/library/os.html

    Reference for the URL syntax for S3 objects in buckets:
    https://stackoverflow.com/questions/48608570/python-3-boto-3-aws-s3-get-object-url

    Python documentation for the built-in open function:
    https://docs.python.org/3/library/functions.html#open

    :param ec2_instance_id: EC2 instance ID to be displayed in the document
    :param ec2_instance_availability_zone: EC2 instance availability zone to be displayed in the document
    :param s3_object_details: Data returned from creation of an S3 object
    """
    # https://docs.python.org/3/library/os.html
    try:
        if os.path.exists("index.html"): # since hard-coded, need to existence check
            os.remove("index.html")
    except OSError as os_err:
        raise OSError(f"OS error when removing the existing index.html document, check permissions, running processes, and file path: {os_err}")


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
    <img src="https://{s3_object_details['BucketName']}.s3.amazonaws.com/{s3_object_details['ObjKey']}" style="max-width: 600px; height: auto;">
    </body>
    </html>
    """
    try:
        with open("index.html", "w") as file:  # just with open and args
            file.write(ec2_html_script)
    except OSError as os_err:
        print(f'OS error when creating the index.html document, check permissions, duplicates, and file path: {os_err}')

def delete_index_document():
    """
    Deletes the local index.html file.

    Python documentation for the os module's remove() function:
    https://docs.python.org/3/library/os.html#os.remove
    """
    try:
        if os.path.exists("index.html"): # existence check
            os.remove("index.html")
    except OSError as os_err:
        raise OSError(f"OS error when deleting the index.html document, check permissions, running processes, and file path: {os_err}")

def check_httpd_active(instance):
    """
    Uses the subprocess module to connect to the argument EC2 instance resource and check if the httpd
    service (Apache web server) is active.

    Python documentation for the find() function:
    https://docs.python.org/3/library/stdtypes.html#str.find

    Python documentation for the subprocess module:
    https://docs.python.org/3/library/subprocess.html

    :param instance: EC2 instance resource to be checked
    :return: True if the httpd service is active, False if not.
    """
    # https://docs.python.org/3/library/subprocess.html
    try:
        result = subprocess.run([
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            "JOMahony_A01_RSA.pem",
            f"ec2-user@{instance.public_ip_address}",
            "service httpd status"
        ], text=True, capture_output=True)

        # "Active: active (running)" shows when actually running alongside PID, etc.
        if result.stdout.find("Active: active (running)") > 0: # -1 == not found
            return True

        return False
    except subprocess.CalledProcessError as subprocess_err:
        print(f'Subprocess error when connecting to EC2 instance to check httpd status: {subprocess_err}')
        raise

def transfer_index_to_ec2(instance):
    """
    Transfers the local index.html file to the argument EC2 instance's /var/www/html directory.

    Function:
    - Uses SCP over TCP/22 with the local pem key to transfer the local index.html file to the ec2-user directory.
    - Uses SSH to connect and move index.html from the ec2-user directory to /var/www/html/
    - StrictHostKeyChecking is disabled as a workaround to Amazon requiring an initial 'yes' to add the host key.
    - If the connection or transfer fails, a CalledProcessError is thrown.

    Python documentation for the subprocess module:
    https://docs.python.org/3/library/subprocess.html

    Python documentation for the subprocess.run() check option:
    https://docs.python.org/3.14/library/subprocess.html#subprocess.check

    :param instance: EC2 instance resource to receive index.html
    """
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

def get_server_access_log(instance):
    """
    Connects to the argument instance via SSH and counts how many HTTP requests
    have been made to the web server.

    - Uses /var/log/httpd/access_log to count HTTP requests.
    - access_log will be empty without any requests made.
    - Uses command: sudo cat /var/log/httpd/access_log

    Apache documentation for web server logs:
    https://httpd.apache.org/docs/2.4/logs.html

    :param instance: EC2 instance handle
    :return: Count of how many HTTP requests the server has received
    """
    result = subprocess.run([
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        "JOMahony_A01_RSA.pem",
        f"ec2-user@{instance.public_ip_address}",
        "sudo cat /var/log/httpd/access_log"
    ], text=True, capture_output=True)
    # [ec2-user@ip-172-31-24-80 log]$ sudo cat /var/log/httpd/access_log
    # X.X.X.X - - [25/Mar/2026:16:27:46 +0000] "GET / HTTP/1.1" 200 481 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0"
    # X.X.X.X - - [25/Mar/2026:16:27:47 +0000] "GET /favicon.ico HTTP/1.1" 404 236 "http://75.101.203.7/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0"

    ctr = 0
    for line in result.stdout.splitlines():
        ctr += 1

    return ctr