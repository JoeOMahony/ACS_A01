import os
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

    # DOCS: KeyMaterial (string) –
    # An unencrypted PEM encoded RSA or ED25519 private key.
    with open('JOMahony_A01_RSA.pem', 'w') as file:
        file.write(response['KeyMaterial'])

    # https://docs.python.org/3/library/os.html
    # octal is used for chmod permissions
    # Key permissions need to be owner read only for EC2 connection or refused
    os.chmod('JOMahony_A01_RSA.pem', 0o400) #
    return response

def delete_remote_key_pair(ec2_client, key_name):
    """
    Deletes the argument key-pair

    Boto3 EC2.Client.delete_key_pair(**kwargs) documentation
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/delete_key_pair.html

    :param ec2_client: EC2 client handle
    :param key_name: Key name of the key-pair to be deleted
    :return: response Dictionary containing success Boolean and KeyPairId String
    """
    response = ec2_client.delete_key_pair(
        KeyName=key_name,
    )

    return response # dict Return Boolean KeyPairId String

def delete_local_key_pair():
    return os.remove('JOMahony_A01_RSA.pem')

def get_all_key_pairs_str(ec2_client):
    key_pairs = ec2_client.describe_key_pairs() # TYPEERROR => { 'KeyPairs': [ {'KeyName': ...}, {'KeyName': ...} ] }

    key_pairs_str = "All Key Pairs:\n"

    for key_pair in key_pairs['KeyPairs']: # Outer dict iterated leaving List of Dictionaries
        key_pairs_str += f"\t{key_pair['KeyName']} | {key_pair['KeyPairId']}\n"

    return key_pairs_str