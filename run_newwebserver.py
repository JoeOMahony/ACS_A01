import sys
import time
import webbrowser
import boto3
import ec2
import s3
import key_pair as kp
from botocore.exceptions import ClientError

divider = '==========================' * 3 # Feel free to change

def get_ec2_handles():
    """
    Gets EC2 client and resource handles from Boto3

    :return: Boto3 client and resource handles
    """
    ec2r = boto3.resource('ec2', region_name='us-east-1')
    ec2c = boto3.client('ec2', region_name='us-east-1')
    return ec2r, ec2c

def get_s3_handles():
    """
    Gets S3 client handle from Boto3

    :return: S3 client handle
    """
    return boto3.client('s3', region_name='us-east-1')

def create_key_pair(ec2_client):
    """
    Creates a remote RSA key pair and locally saves the private key.

    :param ec2_client: EC2 client handle
    :return: Name of the remote key pair
    """
    key_pair = kp.create_key_pair(ec2_client)
    key_name = key_pair['KeyName']
    print(divider)
    print('Creating RSA key-pair...')
    print('\tSuccessfully created remote key-pair with name: ', key_name)
    print('\tSuccessfully created local key with name: JOMahony_A01_RSA.pem')
    print(divider)
    return key_name

def create_ec2_instance(ec2_client, ec2_resource, key_name):
    """
    Creates an EC2 instance

    :param ec2_client: EC2 client handle
    :param ec2_resource: EC2 resource handle
    :param key_name: Name of the remote key pair
    :return: Instance ID, instance availability zone
    """
    print('Creating EC2 instance and waiting for running state...')
    ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, ec2.get_user_data_script())
    ec2_instance_availability_zone = ec2.get_instance_availability_zone(ec2_resource, ec2_instance_id)
    print('\tSuccessfully created instance with ID: ', ec2_instance_id)
    print('\t\tin availability zone: ', ec2_instance_availability_zone)
    print(divider)
    return ec2_instance_id, ec2_instance_availability_zone

def create_s3_bucket(s3_client, ec2_instance_id):
    """
    Creates an S3 bucket

    :param s3_client: S3 client handle
    :param ec2_instance_id: EC2 instance ID
    :return: Dictionary representation of the created S3 bucket
    """
    print('Creating S3 bucket...')
    s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
    print('\tSuccessfully created bucket with name: ', str(s3_bucket['BucketName']))
    print(divider)
    return s3_bucket

def create_s3_object(s3_client, s3_bucket, ec2_instance_id):
    """
    Creates an S3 object inside the argument bucket

    :param s3_client: S3 client handle
    :param s3_bucket: S3 bucket handle
    :param ec2_instance_id: EC2 instance ID
    :return: Dictionary representation of the created S3 object
    """
    obj_url_input = input(
        "Please enter an image URL to be displayed on the website. Enter NONE to use the default image => ").strip()
    image = s3.get_image_object(obj_url_input)
    mime_type = s3.guess_mime_type(obj_url_input)

    s3_object_details = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, image, mime_type)
    print('\tCreating S3 objects to put in bucket...')
    print('\t\tSuccessfully created object with key: ' + str(s3_object_details['ObjKey']))
    print('\t\t\tin bucket with name: ' + str(s3_object_details['BucketName']))
    print(divider)

    return s3_object_details

def configure_remote_instance(ec2_resource, ec2_instance_id, ec2_instance_availability_zone, s3_object_details):
    """
    Configures the remote instance with a dynamic index.html file

    :param ec2_resource: EC2 resource handle
    :param ec2_instance_id:  EC2 instance ID
    :param ec2_instance_availability_zone:  EC2 instance availability zone
    :param s3_object_details:  Dictionary representation of the created S3 object
    :return: EC2 instance resource
    """
    print('Beginning remote configuration...')
    ec2.create_index_document(ec2_instance_id, ec2_instance_availability_zone, s3_object_details)
    instance = ec2_resource.Instance(ec2_instance_id)
    instance.reload()
    ctr = 0
    while not ec2.check_httpd_active(instance):  # in here because I'm keeping all print calls in this script
        ctr += 1
        print(f"\t[{ctr}] Waiting for the web server to come online (refreshes every 15 seconds)")
        time.sleep(15)
        if ctr > 40:
            break
    ec2.transfer_index_to_ec2(instance)
    print('\tSuccessfully completed remote configuration')
    print(divider)
    return instance

def display_web_server_details(instance):
    """
    Displays the public IP and URL of the web server, then asks the user if they'd like it
    automatically opened in a new tab in their browser.

    :param instance: EC2 instance resource
    """
    print('Web server ready for access...')
    print('\tPublic IP address: ', instance.public_ip_address)
    # noinspection HttpUrlsUsage
    print(f"\tWeb address: http://{instance.public_ip_address}")
    # https://docs.python.org/3/library/webbrowser.html
    auto_open_browser = input('Would you like this page automatically opened in your browser? (Y/N) => ')
    if auto_open_browser.strip().upper() == 'Y':
        webbrowser.open_new_tab(f"http://{instance.public_ip_address}")
    print(divider)

def display_log_analysis(instance):
    """
    Dialogue option that allows users to see how many HTTP requests the web server
    received.

    :param instance: EC2 instance resource
    """
    print('Log analysis started...')
    print('\tEnter R to refresh')
    print('\tEnter Q to quit')
    while True:
        user_input = input()
        if user_input.strip().upper() == 'Q':
            return False
        elif user_input.strip().upper() == 'R':
            print('Request counter: ', ec2.get_server_access_log(instance))

def resource_deletion_option():
    """
    Displays the option to delete all resources created for this assignment until the user confirms
    """
    end_flag = False
    while not end_flag:
        user_input = input('To delete all resources created for this assignment, enter DELETE => ')
        if user_input.strip().upper() == 'DELETE':
            break
    print(divider)

def delete_s3_resources(s3_client, s3_bucket):
    """
    Deletes the S3 object and bucket created for this assignment

    :param s3_client: S3 client handle
    :param s3_bucket: Dictionary representation of the S3 bucket
    """
    print('Deleting S3 bucket and objects...')
    bucket_name = s3_bucket['BucketName']
    bucket_objects = s3_client.list_objects(
        Bucket=bucket_name,
    )
    if s3.delete_bucket(s3_client, s3_bucket['BucketName']):
        print('\tSuccessfully deleted bucket object with key: ' + str(bucket_objects['Contents'][0]['Key']))
        print('\tSuccessfully deleted bucket with name: ' + bucket_name)
    print(divider)

def delete_ec2_instance(ec2_client, ec2_resource, ec2_instance_id):
    """
    Deletes the EC2 instance created for this assignment

    :param ec2_client: EC2 client handle
    :param ec2_resource: EC2 resource handle
    :param ec2_instance_id: EC2 instance ID
    """
    print('Deleting EC2 instance...')
    print('\tWaiting for instance state to change to terminated...')
    ec2.terminate_instances(ec2_resource, ec2_client, [ec2_instance_id])
    print('\tSuccessfully terminated instance with ID: ', ec2_instance_id)
    print(divider)

def delete_security_group(ec2_client):
    """
    Deletes the security group created for this assignment

    :param ec2_client: EC2 client handle
    """
    print('Deleting security group...')
    delete_security_group_return = ec2.delete_security_group(ec2_client, 'EC2_public_access')
    try:
        if delete_security_group_return['Return']:
            print('\tSuccessfully deleted security group with name: EC2_public_access')
    except ClientError:  # TypeError: 'ClientError' object is not subscriptable
        print('\tFailed to delete security group with name: EC2_public_access')
        print('\tPlease ensure there are no resources previously created by this program tied to this security group')
        print('\t\tThis error is thrown when this program is run after previously being interrupted and unable to remove resources')
    print(divider)

def delete_key_pair(ec2_client, key_name):
    """
    Deletes the remote key-pair and local pem key created for this assignment

    :param ec2_client: EC2 client handle
    :param key_name: Remote key name
    """
    print('Remotely and locally deleting RSA key-pair...')
    delete_remote_key_pair_return = kp.delete_remote_key_pair(ec2_client, key_name)
    if delete_remote_key_pair_return['Return']:
        print('\tSuccessfully deleted remote key-pair with name: ' + key_name)
    delete_local_key_pair_return = kp.delete_local_key_pair()
    if delete_local_key_pair_return is None:
        print('\tSuccessfully deleted local key with name: JOMahony_A01_RSA.pem')
    print(divider)

def delete_index_document():
    """
    Deletes the index.html document created for this assignment
    """
    print('Deleting HTML index document...')
    delete_index_document_return = ec2.delete_index_document()
    if delete_index_document_return is None:
        print('\tSuccessfully deleted index.html document')
    print(divider)

def display_program_completion():
    """
    Displays the program completion message
    """
    print('Program complete...')
    print(divider)

def main():
    """
    Main function to co-ordinate the execution of the entire assignment program
    """
    # AWS API handles
    ec2_resource, ec2_client = get_ec2_handles()
    s3_client = get_s3_handles()

    # Key-pair creation
    key_name = create_key_pair(ec2_client)

    # EC2 instance creation
    ec2_instance_id, ec2_instance_availability_zone = create_ec2_instance(ec2_client, ec2_resource, key_name)

    # S3 bucket creation
    s3_bucket = create_s3_bucket(s3_client, ec2_instance_id)

    # S3 object creation
    s3_object_details = create_s3_object(s3_client, s3_bucket, ec2_instance_id)

    # Remote configuration
    instance = configure_remote_instance(ec2_resource, ec2_instance_id, ec2_instance_availability_zone, s3_object_details)

    # Display web server details
    display_web_server_details(instance)

    # UI loop for log analysis
    display_log_analysis(instance)

    # UI loop for deletion
    resource_deletion_option()

    # S3 bucket and objects deletion
    delete_s3_resources(s3_client, s3_bucket)

    # EC2 instance deletion
    delete_ec2_instance(ec2_client, ec2_resource, ec2_instance_id)

    # Security group deletion
    delete_security_group(ec2_client)

    # Key-pair deletion
    delete_key_pair(ec2_client, key_name)

    # index document deletion
    delete_index_document()

    # Program completion notice
    display_program_completion()

    # Exit program
    sys.exit(0)

if __name__ == "__main__":
    main()