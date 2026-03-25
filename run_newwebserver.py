import time
import boto3
import ec2
import s3
import key_pair as kp
from botocore.exceptions import ClientError

divider = '=========================='*3

# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')
s3_resource = boto3.resource('s3', region_name='us-east-1')

# Key-pair creation
key_pair = kp.create_key_pair(ec2_client)
key_name = key_pair['KeyName']
print(divider)
print('Creating RSA key-pair...')
print('\tSuccessfully created remote key-pair with name: ', key_name)
print('\tSuccessfully created local key with name: JOMahony_A01_RSA.pem')
print(divider)

# EC2 instance creation
print('Creating EC2 instance and waiting for running state...')
ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, ec2.get_user_data_script())
ec2_instance_availability_zone = ec2.get_instance_availability_zone(ec2_resource, ec2_instance_id)
print('\tSuccessfully created instance with ID: ', ec2_instance_id)
print('\t\tin availability zone: ', ec2_instance_availability_zone)
print(divider)

# S3 bucket creation
print('Creating S3 bucket...')
s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('\tSuccessfully created bucket with name: ', str(s3_bucket['BucketName']))
print(divider)

# S3 object creation
obj_url_input = input("Please enter an image URL to be displayed on the website. Enter NONE to use the default image => ").strip()
image = s3.get_image_object(obj_url_input)
mime_type = s3.guess_mime_type(obj_url_input)

s3_object_details = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, image, mime_type)
print('\tCreating S3 objects to put in bucket...')
print('\t\tSuccessfully created object with key: ' + str(s3_object_details['ObjKey']))
print('\t\t\tin bucket with name: ' + str(s3_object_details['BucketName']))
print(divider)

# Remote configuration
print('Beginning remote configuration...')
ec2.create_index_document(ec2_instance_id, ec2_instance_availability_zone, s3_object_details)
instance = ec2_resource.Instance(ec2_instance_id)
instance.reload()
ctr = 0
while not ec2.check_httpd_active(instance): # in here because I'm keeping all print calls in this script
    ctr += 1
    print(f"\t[{ctr}] Waiting for the web server to come online (refreshes every 15 seconds)")
    time.sleep(15)
    if ctr > 40:
        break
ec2.transfer_index_to_ec2(instance)
print('\tSuccessfully completed remote configuration')
print(divider)

# IP display
print('Web server ready for access...')
print('\tPublic IP address: ', instance.public_ip_address)
# noinspection HttpUrlsUsage
print(f"\tWeb address: http://{instance.public_ip_address}")
print(divider)

# UI loop for deletion
end_flag = False
while not end_flag:
    user_input = input('To delete all resources created for this assignment, enter DELETE => ')
    if user_input.strip().upper() == 'DELETE':
        end_flag = True
print(divider)

# S3 bucket and objects deletion
print('Deleting S3 bucket and objects...')
bucket_name = s3_bucket['BucketName']
bucket_objects = s3_client.list_objects(
        Bucket=bucket_name,
    )
if s3.delete_bucket(s3_client, s3_bucket['BucketName']):
    print('\tSuccessfully deleted bucket object with key: ' + str(bucket_objects['Contents'][0]['Key']))
    print('\tSuccessfully deleted bucket with name: ' + bucket_name)
print(divider)

# EC2 instance deletion
print('Deleting EC2 instance...')
print('\tWaiting for instance state to change to terminated...')
ec2.terminate_instances(ec2_resource, ec2_client, [ec2_instance_id])
print('\tSuccessfully terminated instance with ID: ', ec2_instance_id)
print(divider)

# Security group deletion
print('Deleting security group...')
delete_security_group_return = ec2.delete_security_group(ec2_client, 'EC2_public_access')
try:
    if delete_security_group_return['Return']:
        print('\tSuccessfully deleted security group with name: EC2_public_access')
except ClientError: # TypeError: 'ClientError' object is not subscriptable
    print('\tFailed to delete security group with name: EC2_public_access')
    print('\tPlease ensure there are no resources previously created by this program tied to this security group')
    print('\t\tThis error is thrown when this program is run after previously being interrupted and unable to remove resources')
print(divider)

# Key-pair deletion
print('Remotely and locally deleting RSA key-pair...')
delete_remote_key_pair_return = kp.delete_remote_key_pair(ec2_client, key_name)
if delete_remote_key_pair_return['Return']:
    print('\tSuccessfully deleted remote key-pair with name: ' + key_name)
delete_local_key_pair_return = kp.delete_local_key_pair()
if delete_local_key_pair_return is None:
    print('\tSuccessfully deleted local key with name: JOMahony_A01_RSA.pem')
print(divider)

# index document deletion
print('Deleting HTML index document...')
delete_index_document_return = ec2.delete_index_document()
if delete_index_document_return is None:
    print('\tSuccessfully deleted index.html document')
print(divider)

# Program completion notice
print('Program complete...')
print(divider)