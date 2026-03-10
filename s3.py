def create_bucket(s3_client, ec2_instance_id):

    bucket_name = 'joe-omahony-' + ec2_instance_id

    bucket = s3_client.create_bucket(
        ACL='public-read',
        Bucket=bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': 'us-east-1',
            'Tags': [
                        {'Key': 'CreatedBy', 'Value': 'JoeOMahony'},
                        {'Key': 'Module', 'Value': 'AutomatedCloudServices'},
                        {'Key': 'Assignment', 'Value': 'Assignment01'}
                    ],
        },
        ObjectLockEnabledForBucket=False, # Check later
    )

    return bucket

