import boto3
import ec2
import s3
from create_key_pair import create_key_pair

# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

s3_client = boto3.client('s3', region_name='us-east-1')
s3_resource = boto3.resource('s3', region_name='us-east-1')

# Key pair
key_pair = create_key_pair(ec2_client)
key_name = key_pair['KeyName']


ec2_instance_id = ec2.create_instance(ec2_resource, ec2_client, key_name)
print('==========================')
print('EC2 Instance created with ID: ', ec2_instance_id)
print('==========================')

s3_bucket = s3.create_bucket(s3_client, ec2_instance_id)
print('S3 Bucket created : ', s3_bucket)
print('==========================')