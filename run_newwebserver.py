import time
import subprocess
import boto3
import ec2
import s3
import key_pair as kp

ec2_data_script = """#!/bin/bash
dnf update
dnf upgrade -y
dnf install -y httpd
systemctl enable httpd
systemctl start httpd
"""

divider = '=========================='*3

# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

s3_client = boto3.client('s3', region_name='us-east-1')
s3_resource = boto3.resource('s3', region_name='us-east-1')

# Key pair
key_pair = kp.create_key_pair(ec2_client)
key_name = key_pair['KeyName']
print(divider)
print('Creating RSA key-pair...')
print('\tSuccessfully created remote key-pair with name: ', key_name)
print('\tSuccessfully created local key with name: JOMahony_A01_RSA.pem')
print(divider)

print('Creating EC2 instance and waiting for running state...')
ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, ec2_data_script)
ec2_instance_availability_zone = ec2.get_instance_availability_zone(ec2_resource, ec2_instance_id)
print('\tSuccessfully created instance with ID: ', ec2_instance_id)
print('\t\tin availability zone: ', ec2_instance_availability_zone)
print(divider)

print('Creating S3 bucket...')
s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('\tSuccessfully created bucket with name: ', str(s3_bucket['BucketName']))
print(divider)

obj_url_input = input("Please enter an image URL to be displayed on the website. Enter NONE to use the default image => ").strip()
image = s3.get_image_object(obj_url_input)
mime_type = s3.guess_mime_type(obj_url_input)

    # obj_url_input = 'https://www.setu.ie/imager/ctas/35068/Cork-Road-Campus-Waterford-3_a1dcb81403a2f417e019929f519bbb18.jpg?width=360'
# setu_image = open('images/setu.png','rb') # docs specify must be opened in binary mode, then specify MIME type
# # https://docs.aws.amazon.com/boto3/latest/guide/s3-uploading-files.html

s3_object_details = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, image, mime_type)

# {'BucketName': 'joe-omahony-i-00eb297585ef6df93', 'ObjKey': 'joe-omahony-i-00eb297585ef6df93-obj-1774359755187547000'}
print('\tCreating S3 objects to put in bucket...')
print('\t\tSuccessfully created object with key: ' + str(s3_object_details['ObjKey']))
print('\t\t\tin bucket with name: ' + str(s3_object_details['BucketName']))
print(divider)

# print(ec2.get_all_instances_str(ec2_resource))
# print('==========================')

# print(s3.list_all_buckets(s3_client))
# print('==========================')

# index.html
print('Beginning remote configuration...')
ec2.create_index_document(ec2_instance_id, ec2_instance_availability_zone, s3_object_details)

instance = ec2_resource.Instance(ec2_instance_id)
instance.reload()

# consider move to EC2
def check_apache_running():
    def check_httpd_active():
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

    ctr = 0
    while not check_httpd_active():
        ctr += 1
        print(f"\t[{ctr}] Waiting for the web server to come online (refreshes every 15 seconds)")
        time.sleep(15)

        if ctr > 40:
            break

check_apache_running()

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
], check=True) # Silent fail without, continues on

subprocess.run([
    "ssh",
    "-o",
    "StrictHostKeyChecking=no",
    "-i",
    "JOMahony_A01_RSA.pem",
    f"ec2-user@{instance.public_ip_address}",
    "sudo mv ~/index.html /var/www/html/index.html"
], check=True)
print('\tSuccessfully completed remote configuration')
print(divider)

print('Web server ready for access...')
print('\tPublic IP address: ', instance.public_ip_address)
print(f"\tWeb address: http://{instance.public_ip_address}")
print(divider)

end_flag = False
while not end_flag:
    user_input = input('To delete all resources created for this assignment, enter DELETE => ')
    if user_input.strip().upper() == 'DELETE':
        end_flag = True
print(divider)

print('Deleting S3 bucket and objects...')
bucket_name = s3_bucket['BucketName']
bucket_objects = s3_client.list_objects(
        Bucket=bucket_name,
    )
if s3.delete_bucket(s3_client, s3_bucket['BucketName']):
    print('\tSuccessfully deleted bucket object with key: ' + str(bucket_objects['Contents'][0]['Key']))
    print('\tSuccessfully deleted bucket with name: ' + bucket_name)
print(divider)

# print(s3.list_all_buckets(s3_client))
# print(divider)

print('Deleting EC2 instance...')
print('\tWaiting for instance state to change to terminated...')
ec2.terminate_instances(ec2_resource, ec2_client, [ec2_instance_id])
print('\tSuccessfully terminated instance with ID: ', ec2_instance_id)
print(divider)

print('Deleting security group...')
delete_security_group_return = ec2.delete_security_group(ec2_client, 'EC2_public_access')
if delete_security_group_return['Return']:
    print('\tSuccessfully deleted security group with name: EC2_public_access')
print(divider)

print('Remotely and locally deleting RSA key-pair...')
delete_remote_key_pair_return = kp.delete_remote_key_pair(ec2_client, key_name)
if delete_remote_key_pair_return['Return']:
    print('\tSuccessfully deleted remote key-pair with name: ' + key_name)
delete_local_key_pair_return = kp.delete_local_key_pair()
if delete_local_key_pair_return is None:
    print('\tSuccessfully deleted local key with name: JOMahony_A01_RSA.pem')
print(divider)

print('Deleting HTML index document...')
delete_index_document_return = ec2.delete_index_document()
if delete_index_document_return is None:
    print('\tSuccessfully deleted index.html document')
print(divider)

print('Program complete...')
print(divider)

# print('All unterminated EC2 instance IDs: ', str(ec2.get_unterminated_instances(ec2_resource)))
# print('==========================')

# print('Deleting all unterminated EC2 Instances...')
# print(str(ec2.terminate_instances(ec2_resource, ec2.get_unterminated_instances(ec2_resource))))
# # (InvalidInstanceID.Malformed) without str() call
# print('==========================')
#
# print(ec2.get_all_instances_str(ec2_resource))
# print('==========================')
#
# print(kp.get_all_key_pairs_str(ec2_client))
# print('==========================')