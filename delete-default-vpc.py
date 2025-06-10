import argparse
import time

import boto3

with open("aws-profiles.txt") as f:
    profiles = f.read().splitlines()


def delete_internet_gateways(client, vpc_id):
    igws = client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["InternetGateways"]
    print("Internet Gateways attached to the VPC:", len(igws))
    for igw in igws:
        igw_id = igw["InternetGatewayId"]
        print("Detaching and deleting Internet Gateway:", igw_id)
        try:
            client.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        except Exception as e:
            print("Error detaching IGW:", e)
        client.delete_internet_gateway(InternetGatewayId=igw_id)


def delete_nat_gateways(client, vpc_id):
    nat_gateways = client.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["NatGateways"]
    print("NAT Gateways in the VPC:", len(nat_gateways))
    for nat in nat_gateways:
        nat_id = nat["NatGatewayId"]
        print("Deleting NAT Gateway:", nat_id)
        client.delete_nat_gateway(NatGatewayId=nat_id)
        # Wait for the NAT gateway to be deleted
        while True:
            nat_status = client.describe_nat_gateways(NatGatewayIds=[nat_id])[
                "NatGateways"
            ][0]["State"]
            if nat_status in ["deleted", "failed"]:
                break
            print("Waiting for NAT Gateway", nat_id, "to delete...")
            time.sleep(5)


def delete_route_tables(client, vpc_id):
    rtbs = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    print("Route tables in the VPC:", len(rtbs))
    for rtb in rtbs:
        is_main = any(assoc.get("Main", False) for assoc in rtb.get("Associations", []))
        if not is_main:
            rtb_id = rtb["RouteTableId"]
            print("Deleting route table:", rtb_id)
            client.delete_route_table(RouteTableId=rtb_id)


def delete_subnets(client, vpc_id):
    subnets = client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
        "Subnets"
    ]
    print("Subnets in the VPC:", len(subnets))
    for subnet in subnets:
        subnet_id = subnet["SubnetId"]
        print("Deleting subnet:", subnet_id)
        client.delete_subnet(SubnetId=subnet_id)


def delete_vpc(client, vpc_id):
    print("Deleting VPC:", vpc_id)
    client.delete_vpc(VpcId=vpc_id)
    print("Deletion initiated.")


def delete_default_vpc_in_region(session, region):
    ec2 = session.resource("ec2", region_name=region)
    client = session.client("ec2", region_name=region)
    vpcs = list(ec2.vpcs.filter(Filters=[{"Name": "isDefault", "Values": ["true"]}]))
    if not vpcs:
        print(f"No default VPC found in region: {region}")
        return
    vpc = vpcs[0]
    vpc_id = vpc.id
    print(f"Default VPC in region {region}: {vpc_id}")
    #delete_internet_gateways(client, vpc_id)
    #delete_nat_gateways(client, vpc_id)
    #delete_route_tables(client, vpc_id)
    #delete_subnets(client, vpc_id)
    #delete_vpc(client, vpc_id)


def delete_default_vpcs_all_regions(profile):
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client("ec2", region_name="us-east-1")
    regions = client.describe_regions(AllRegions=True)["Regions"]
    for r in regions:
        region_name = r["RegionName"]
        opt_in_status = r.get("OptInStatus", "opt-in-not-required")
        if opt_in_status in ("opt-in-not-required", "opted-in"):
            print(f"Processing region: {region_name}")
            delete_default_vpc_in_region(session, region_name)
        else:
            print(f"Skipping region: {region_name} with optInStatus: {opt_in_status}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete default VPC for a provided AWS profile in all opted-in regions."
    )
    parser.add_argument("--profile", help="AWS profile name.")
    args = parser.parse_args()
    if args.profile:
        print(f"Deleting default VPCs for provided profile: {args.profile}")
        delete_default_vpcs_all_regions(args.profile)
    else:
        for profile in profiles:
            print(f"Deleting default VPCs for profile: {profile}")
            delete_default_vpcs_all_regions(profile)


if __name__ == "__main__":
    main()
