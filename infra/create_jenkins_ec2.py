#!/usr/bin/env python3
"""
Provision an AWS EC2 instance (Free Tier) with Jenkins pre-installed.

Usage:
    pip install boto3
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_DEFAULT_REGION=us-east-1   # or your preferred region

    python create_jenkins_ec2.py

The script will:
    - Create a security group (SSH + HTTP + Jenkins 8080)
    - Create a key pair (downloads .pem file)
    - Launch a t2.micro Ubuntu instance with Jenkins installed via user-data
    - Print the public IP and SSH command
"""

import os
import sys
import time
import stat

import boto3
from botocore.exceptions import ClientError

# ------------------ Configuration ------------------
INSTANCE_NAME = "bghi7-jenkins"
INSTANCE_TYPE = "t3.micro"  # Free Tier eligible (t2.micro not Free Tier in newer accounts)
KEY_NAME = "bghi7-jenkins-key"
SECURITY_GROUP_NAME = "bghi7-jenkins-sg"

# Ubuntu 22.04 LTS AMI IDs (update if needed for your region)
# These are official Canonical AMIs; the script will try to find the latest automatically.
# Fallback AMI for us-east-1 if lookup fails:
FALLBACK_AMI = "ami-0c7217cdde317cfec"  # Ubuntu 22.04 us-east-1 (check for updates)

# User-data script to install Java + Jenkins on first boot
USER_DATA = """#!/bin/bash
set -euxo pipefail

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y openjdk-17-jre git python3-venv python3-pip nginx

# Add Jenkins repo and install
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | tee /etc/apt/sources.list.d/jenkins.list > /dev/null
apt-get update -y
apt-get install -y jenkins

# Start Jenkins
systemctl enable jenkins
systemctl start jenkins

# Print initial admin password location
echo "Jenkins installed. Initial admin password at: /var/lib/jenkins/secrets/initialAdminPassword"
"""


def get_default_vpc(ec2_client):
    """Get the default VPC ID."""
    response = ec2_client.describe_vpcs(
        Filters=[{"Name": "isDefault", "Values": ["true"]}]
    )
    vpcs = response.get("Vpcs", [])
    if not vpcs:
        raise RuntimeError("No default VPC found. Create one or modify the script.")
    return vpcs[0]["VpcId"]


def get_ubuntu_ami(ec2_client):
    """Find the latest Ubuntu 22.04 LTS AMI."""
    try:
        response = ec2_client.describe_images(
            Owners=["099720109477"],  # Canonical
            Filters=[
                {"Name": "name", "Values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
                {"Name": "state", "Values": ["available"]},
                {"Name": "architecture", "Values": ["x86_64"]},
            ],
        )
        images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
        if images:
            return images[0]["ImageId"]
    except ClientError as e:
        print(f"Warning: Could not lookup AMI ({e}), using fallback.")
    return FALLBACK_AMI


def create_security_group(ec2_client, vpc_id, my_ip):
    """Create a security group for Jenkins."""
    try:
        response = ec2_client.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description="Security group for Jenkins EC2 (BGHI7)",
            VpcId=vpc_id,
        )
        sg_id = response["GroupId"]
        print(f"Created security group: {sg_id}")
    except ClientError as e:
        if "InvalidGroup.Duplicate" in str(e):
            # Already exists, find it
            response = ec2_client.describe_security_groups(
                Filters=[
                    {"Name": "group-name", "Values": [SECURITY_GROUP_NAME]},
                    {"Name": "vpc-id", "Values": [vpc_id]},
                ]
            )
            sg_id = response["SecurityGroups"][0]["GroupId"]
            print(f"Security group already exists: {sg_id}")
            return sg_id
        raise

    # Add inbound rules
    my_ip_cidr = f"{my_ip}/32"
    rules = [
        # SSH from your IP only
        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": my_ip_cidr, "Description": "SSH from my IP"}]},
        # HTTP from anywhere (for the Django app)
        {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP"}]},
        # Jenkins from your IP only
        {"IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "IpRanges": [{"CidrIp": my_ip_cidr, "Description": "Jenkins from my IP"}]},
    ]

    try:
        ec2_client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=rules)
        print("Added inbound rules to security group.")
    except ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            print("Inbound rules already exist.")
        else:
            raise

    return sg_id


def create_key_pair(ec2_client):
    """Create a key pair and save the .pem file locally."""
    pem_path = os.path.join(os.getcwd(), f"{KEY_NAME}.pem")

    try:
        response = ec2_client.create_key_pair(KeyName=KEY_NAME, KeyType="rsa")
        private_key = response["KeyMaterial"]
        with open(pem_path, "w") as f:
            f.write(private_key)
        os.chmod(pem_path, stat.S_IRUSR)  # chmod 400
        print(f"Created key pair and saved to: {pem_path}")
    except ClientError as e:
        if "InvalidKeyPair.Duplicate" in str(e):
            print(f"Key pair '{KEY_NAME}' already exists. Reusing it.")
            if not os.path.exists(pem_path):
                print(f"WARNING: Key pair exists in AWS but {pem_path} not found locally.")
                print("         You may need to delete the key pair in AWS and re-run, or use your existing .pem file.")
        else:
            raise

    return KEY_NAME, pem_path


def launch_instance(ec2_resource, ami_id, sg_id, key_name):
    """Launch the EC2 instance."""
    print(f"Launching EC2 instance ({INSTANCE_TYPE}, AMI: {ami_id})...")

    instances = ec2_resource.create_instances(
        ImageId=ami_id,
        InstanceType=INSTANCE_TYPE,
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        UserData=USER_DATA,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": INSTANCE_NAME}],
            }
        ],
    )

    instance = instances[0]
    print(f"Instance ID: {instance.id}")
    print("Waiting for instance to be running...")

    instance.wait_until_running()
    instance.reload()

    return instance


def get_my_ip():
    """Get your public IP address."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=5) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        pass
    try:
        with urllib.request.urlopen("https://ifconfig.me", timeout=5) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        print("Could not determine your public IP. Please enter it manually.")
        return input("Your public IP: ").strip()


def main():
    print("=" * 60)
    print("BGHI7 Jenkins EC2 Provisioning Script")
    print("=" * 60)

    # Check AWS credentials
    if not os.getenv("AWS_ACCESS_KEY_ID") and not os.path.exists(os.path.expanduser("~/.aws/credentials")):
        print("ERROR: AWS credentials not found.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or configure ~/.aws/credentials")
        sys.exit(1)

    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    print(f"Region: {region}")

    ec2_client = boto3.client("ec2", region_name=region)
    ec2_resource = boto3.resource("ec2", region_name=region)

    # Get your public IP
    my_ip = get_my_ip()
    print(f"Your public IP: {my_ip}")

    # Get default VPC
    vpc_id = get_default_vpc(ec2_client)
    print(f"Using VPC: {vpc_id}")

    # Get Ubuntu AMI
    ami_id = get_ubuntu_ami(ec2_client)
    print(f"Ubuntu AMI: {ami_id}")

    # Create security group
    sg_id = create_security_group(ec2_client, vpc_id, my_ip)

    # Create key pair
    key_name, pem_path = create_key_pair(ec2_client)

    # Launch instance
    instance = launch_instance(ec2_resource, ami_id, sg_id, key_name)

    public_ip = instance.public_ip_address
    print()
    print("=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"Instance ID   : {instance.id}")
    print(f"Public IP     : {public_ip}")
    print(f"Key file      : {pem_path}")
    print()
    print("Wait ~3-5 minutes for Jenkins to install, then:")
    print()
    print(f"  1) SSH into the instance:")
    print(f"     ssh -i {pem_path} ubuntu@{public_ip}")
    print()
    print(f"  2) Get Jenkins initial admin password:")
    print(f"     sudo cat /var/lib/jenkins/secrets/initialAdminPassword")
    print()
    print(f"  3) Open Jenkins in your browser:")
    print(f"     http://{public_ip}:8080")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
