# SAMPLE USE:
# python s3_list_buckets.py
#
#
import datetime
import boto3


ec2r = boto3.resource('ec2')

instance = ec2r.create_instances(
    ImageId='ami-0f3caa1cf4417e51b',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    SecurityGroups=['default'],
    KeyName='acs_a01_jomahony',
    TagSpecifications=[
        {
            "Tags": [
                {"Key": "CreatedBy", "Value": "JoeOMahony"},
                {"Key": "Module", "Value": "AutomatedCloudServices"},
                {"Key": "Assignment", "Value": "Assignment01"}
            ]
        }
    ]
)

print(instance[0].id)