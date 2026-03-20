import boto3
import ec2
import s3
from key_pair import create_key_pair, get_all_key_pairs_str, delete_key_pair

sample_script = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl enable httpd
systemctl start httpd
echo "<h1>Web server is working</h1>" > /var/www/html/index.html
"""
# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

s3_client = boto3.client('s3', region_name='us-east-1')
s3_resource = boto3.resource('s3', region_name='us-east-1')

# Key pair
key_pair = create_key_pair(ec2_client)
key_name = key_pair['KeyName']
print('==========================')
print('RSA Key Pair created with name: ', key_name)
print('==========================')

ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, sample_script)
print('EC2 Instance created with ID: ', ec2_instance_id)
print('==========================')

s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('S3 Bucket created : ', str(s3_bucket)) # TypeError
print('==========================')

setu_image = open('images/setu.png','rb') # docs specify must be opened in binary mode, then specify MIME type
# https://docs.aws.amazon.com/boto3/latest/guide/s3-uploading-files.html

obj = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, setu_image)
print('S3 object created and put in bucket: ' + str(obj))
print('==========================')

print(ec2.get_all_instances_str(ec2_resource))
print('==========================')

print('All unterminated EC2 instance IDs: ', str(ec2.get_unterminated_instances(ec2_resource)))
print('==========================')
#
# print('Deleting all unterminated EC2 Instances...')
# print(str(ec2.terminate_instances(ec2_resource, ec2.get_unterminated_instances(ec2_resource))))
# # (InvalidInstanceID.Malformed) without str() call
# print('==========================')
#
# print(ec2.get_all_instances_str(ec2_resource))
# print('==========================')
#
# print(get_all_key_pairs_str(ec2_client))
# print('==========================')
#
# print('Deleting the key pair created for this assignment...')
# print(delete_key_pair(ec2_client, key_name))
# print('==========================')
#
# print(get_all_key_pairs_str(ec2_client))
# print('==========================')