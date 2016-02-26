#!/usr/bin/python
# coding: utf-8
from __future__ import absolute_import, unicode_literals, print_function

"""
This script assumes that you have
AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY configured via env var
or via boto.cfg
"""

import json
import sys
import argparse

try:
    from boto.exception import BotoServerError
    from boto import ec2
    from boto.ec2.connection import EC2Connection
    from boto.ec2 import elb
except ImportError:
    print("You must install boto library: 'pip install boto'")


def create_arg_parser():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--host', help='get running host specific information')
    group.add_argument('--list', action='store_true',
                       help="List running hosts in elb")
    return parser


def get_elb_connection(region_name):
    return elb.connect_to_region(region_name)


def get_ec2_connection(region_name):
    ec2_region = ec2.get_region(region_name=region_name)
    return EC2Connection(region=ec2_region)


def get_running_instances_in_elb(load_balancer_name, region):
    elb_conn = get_elb_connection(region)
    ec2_conn = get_ec2_connection(region)
    elbs = elb_conn.get_all_load_balancers(
        load_balancer_names=[load_balancer_name])
    instance_ids = [instance.id for instance in elbs[0].instances]
    reservations = ec2_conn.get_all_instances(instance_ids)
    return [instance for r in reservations
            for instance in r.instances if instance.state == 'running']


if __name__ == '__main__':
    parser = create_arg_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    try:
        instances = get_running_instances_in_elb(args.load_balancer_name)
    except BotoServerError as e:
        print ("Something went wrong: %s | error_code: %s"
               % (e.message, e.error_code))
        sys.exit(1)
    if args.list:
        inventory = {
            'web': {
                'hosts': [instance.public_dns_name for instance in instances]
            }
        }
    if args.host:
        try:
            instance = next(
                instance for instance in instances
                if instance.public_dns_name == args.host)
        except StopIteration:
            inventory = {}
        else:
            inventory = {"ansible_ssh_host": instance.ip_address}
    json.dump(inventory, sys.stdout)
