import boto3
import ec2
import s3
from key_pair import create_key_pair, delete_key_pair

ec2_data_script = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl enable httpd
systemctl start httpd
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

ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name, ec2_data_script)
ec2_instance_availability_zone = ec2.get_instance_availability_zone(ec2_resource, ec2_instance_id)
print('EC2 Instance created with ID: ', ec2_instance_id)
print('==========================')

s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('S3 Bucket created : ', str(s3_bucket)) # TypeError
print('==========================')

setu_image = open('images/setu.png','rb') # docs specify must be opened in binary mode, then specify MIME type
# https://docs.aws.amazon.com/boto3/latest/guide/s3-uploading-files.html

obj_details = s3.put_object(s3_client, s3_bucket['BucketName'], ec2_instance_id, setu_image)
print('S3 object created and put in bucket: ' + str(obj_details))
print('==========================')

print(ec2.get_all_instances_str(ec2_resource))
print('==========================')

print(s3.list_all_buckets(s3_client))
print('==========================')

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
<img src="https://{obj_details['BucketName']}.s3.amazonaws.com/{obj_details['ObjKey']}">
</body>
</html>
"""

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
print(delete_key_pair(ec2_client, key_name))
print('==========================')

# print('All unterminated EC2 instance IDs: ', str(ec2.get_unterminated_instances(ec2_resource)))
# print('==========================')
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