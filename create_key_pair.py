import time

def create_key_pair(ec2_client):
    """
    Creates a unique RSA key-pair using the EC2 client handle

    - Uniqueness provided through nanoseconds since Epoch (1/Jan/70)
    -- Nanoseconds selected to ensure uniqueness, but also because time.time_ns() returns an int
    - Docs: https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/create_key_pair.html
    - Key name: acs_a01_jomahony

    :param ec2_client: EC2 client handle
    :return: dict Dictionary describing the key-pair (note KeyName)
    """
    key_name = f"acs_a01_jomahony_{time.time_ns()}" # using nanoseconds from Epoch to make each instance key unique
    response = ec2_client.create_key_pair(
        KeyName=key_name,
        KeyType='rsa',
        KeyFormat='pem',
        TagSpecifications=[
            {
                "ResourceType": "key-pair",
                "Tags": [
                    {"Key": "CreatedBy", "Value": "JoeOMahony"},
                    {"Key": "Module", "Value": "AutomatedCloudServices"},
                    {"Key": "Assignment", "Value": "Assignment01"}
                ]
            }
        ]
    )
    return response
"""
Basic test for the create_key_pair() function through creating a key and printing the output
"""
# def test_create_key_pair():
#     print(create_key_pair())
# test_create_key_pair()