import boto3

import ec2
from create_key_pair import create_key_pair


# API handler calls
ec2_resource = boto3.resource('ec2', region_name='us-east-1')
ec2_client = boto3.client('ec2', region_name='us-east-1')

key_pair = create_key_pair(ec2_client)
key_name = key_pair['KeyName']

print(ec2.create_instance(ec2_resource, ec2_client, key_name))