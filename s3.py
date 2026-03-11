import time


def create_bucket(s3_client, ec2_instance_id):
    """
    Function which creates a publicly-accessible general purpose S3 bucket and returns a dictionary representation of
    the bucket attributes.

    - Names the bucket using the argument EC2 instance ID as follows, joe-omahony-[ec2_instance_id]
    - Creates the bucket with object lock disabled.
    - Once the bucket exists, the public access block is removed.
    - A dictionary representing the bucket attributes is returned.

    **StackOverflow reference:**
    "How to upload to AWS S3 with Object Tagging" |
    https://stackoverflow.com/questions/55592349/how-to-upload-to-aws-s3-with-object-tagging |
    I couldn't figure out how to add tags, tried the previous way using a dictionary, then the put_object_tagging()
    way, but these both raised ParamValidationError for an Invalid type for parameter Tagging.
    A search resulted in this post, which solved my issue with "Use & as a delimiter between tag values
    like "Key1=Value1"&"Key2=Value2..."

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

    bucket.update({'BucketName': bucket_name})  # bucket Dict only contains ARN/Location, need to add bucket_name

    return bucket

def put_object(s3_client, bucket_name, ec2_instance_id, object):
    """
    Function which puts an object into the S3 bucket.

    AWS documentation on naming S3 objects
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html

    Boto3 documentation on S3.Client.put_object(**kwargs)
    https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html

    :param s3_client:
    :param bucket_name:
    :param object:
    :return:
    """
    # TypeError: can only concatenate str (not "int") to str -> forgot not using f-string
    object_name = 'joe-omahony-' + ec2_instance_id + '-' + 'obj-' + str(time.time_ns()) # max length for obj names is 1024
    response = s3_client.put_object(
        Body=object,
        Bucket=bucket_name,
        Key=object_name,
        # REFERENCE: Full StackOverflow reference for the below Tagging key-pair in function documentation
        Tagging='CreatedBy=JoeOMahony&Module=AutomatedCloudServices&Assignment=AutomatedCloudServices',
    )

    return response
