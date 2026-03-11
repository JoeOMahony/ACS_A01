def create_bucket(s3_client, ec2_instance_id):
    """
    Function which creates a publicly-accessible general purpose S3 bucket and returns a dictionary representation of
    the bucket attributes.

    - Names the bucket using the argument EC2 instance ID as follows, joe-omahony-[ec2_instance_id]
    - Creates the bucket with object lock disabled.
    - Once the bucket exists, the public access block is removed.
    - A dictionary representing the bucket attributes is returned.

    Boto3 documentation for s3_client.create_bucket()
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/create_bucket.html

    Boto3 documentation for S3.Client.get_waiter(waiter_name)
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_waiter.html

    Boto3 documentation for S3 waiters
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3.html#waiters

    Boto3 documentation for S3 BucketExists waiter
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/waiter/BucketExists.html

    Boto3 documentation for s3_client.delete_public_access_block(**kwargs)
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/delete_public_access_block.html

    :param s3_client: S3 Client Handle
    :param ec2_instance_id: EC2 Instance ID used in the bucket name -> joe-omahony-[ec2_instance_id]
    :return: bucket Dictionary with the created bucket's attributes
    """
    bucket_name = 'joe-omahony-' + ec2_instance_id

    bucket = s3_client.create_bucket(
        # ACL='public-read' (InvalidBucketAclWithObjectOwnership)
        # Bucket cannot have ACLs set with ObjectOwnership's BucketOwnerEnforced setting
        Bucket=bucket_name,
        CreateBucketConfiguration={
            # 'LocationConstraint': 'us-east-1', (InvalidLocationConstraint)
            'Tags': [
                        {'Key': 'CreatedBy', 'Value': 'JoeOMahony'},
                        {'Key': 'Module', 'Value': 'AutomatedCloudServices'},
                        {'Key': 'Assignment', 'Value': 'Assignment01'}
                    ],
        },
        ObjectLockEnabledForBucket=False, # Check later
    )

    # could use s3 resource handle instead of below, but will stick with this to match ec2
    waiter = s3_client.get_waiter('bucket_exists') # needed to avoid error with below
    waiter.wait(
        Bucket = bucket_name,
    )

    s3_client.delete_public_access_block(
        Bucket=bucket_name,
    )

    return bucket

