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

# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

s3_client = boto3.client('s3', region_name='us-east-1')
s3_resource = boto3.resource('s3', region_name='us-east-1')

# Key pair
key_pair = kp.create_key_pair(ec2_client)
key_name = key_pair['KeyName']
print('=========================='*2)
print('RSA Key Pair created with name: ', key_name)
print('==========================')

print('Creating EC2 instance and waiting for running state...')
ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, ec2_data_script)
ec2_instance_availability_zone = ec2.get_instance_availability_zone(ec2_resource, ec2_instance_id)
print('EC2 Instance created with ID: ', ec2_instance_id)
print('==========================')

s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('S3 Bucket created : ', str(s3_bucket)) # TypeError
print('==========================')

obj_url_input = input("Please enter an image URL to be displayed on the website or NONE for the default image: ").strip()

if obj_url_input == 'NONE':
    obj_url_input = 'https://upload.wikimedia.org/wikipedia/commons/b/bd/Waterford_Institute_of_Technology%2C_2021-06-01%2C_06.jpg'


    # obj_url_input = 'https://www.setu.ie/imager/ctas/35068/Cork-Road-Campus-Waterford-3_a1dcb81403a2f417e019929f519bbb18.jpg?width=360'
# setu_image = open('images/setu.png','rb') # docs specify must be opened in binary mode, then specify MIME type
# # https://docs.aws.amazon.com/boto3/latest/guide/s3-uploading-files.html

s3_object_details = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, obj_url_input)

print('S3 object created and put in bucket: ' + str(s3_object_details))
print('==========================')

print(ec2.get_all_instances_str(ec2_resource))
print('==========================')

print(s3.list_all_buckets(s3_client))
print('==========================')

# index.html
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
        print(f"[{ctr}] Waiting for the web server to come online...")
        time.sleep(30)

        if ctr > 20:
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



input('delete all?')

print('Deleting the bucket and objects created for this assignment...')
print(s3.delete_bucket(s3_client, s3_bucket['BucketName']))
print('==========================')

print(s3.list_all_buckets(s3_client))
print('==========================')

print('Deleting the EC2 instance created for this assignment...')
print('Waiting for instance state to change to terminated...')
print(ec2.terminate_instances(ec2_resource, ec2_client, [ec2_instance_id]))
print('==========================')

print('Deleting the SG created for this assignment...')
print(ec2.delete_security_group(ec2_client, 'EC2_public_access'))
print('==========================')

print('Deleting the key pair created for this assignment...')
print(kp.delete_remote_key_pair(ec2_client, key_name))
kp.delete_local_key_pair()
print('==========================')

print('Deleting the index file created for this assignment...')
print(ec2.delete_index_document())
print('==========================')

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