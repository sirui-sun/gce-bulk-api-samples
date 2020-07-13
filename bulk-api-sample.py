#!/usr/bin/env python

# -----------------------------------------------------------
# Demonstrates common usage patterns for the GCE Bulk Insert
# APIs, using the googleapiclient SDK.
# 
# email siruisun@google.com for questions
# Reference docs for the googleapiclient library can be found
# http://googleapis.github.io/google-api-python-client/docs/dyn/compute_alpha.html
# -----------------------------------------------------------

import googleapiclient.discovery
import json

# Configuration 
compute = googleapiclient.discovery.build('compute', 'alpha')
project = "grand-sweep-254818"
zone = "us-west1-a"
region = "us-west1"
names = ["instance-1", "instance-2"]
zonal_config = {
   "predefinedNames": names,
   "count":2,
   "instance":{
      "canIpForward":False,
      "deletionProtection":False,
      "disks":[
         {
            "autoDelete":True       ,
            "boot":True,
            "initializeParams":{
               "sourceImage":"https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/family/debian-9"
            },
            "mode":"READ_WRITE",
            "type":"PERSISTENT"
         }
      ],
      "machineType":"https://www.googleapis.com/compute/v1/projects/grand-sweep-254818/zones/{0}/machineTypes/n1-standard-1".format(zone),
      "name":"unused",
      "networkInterfaces":[
         {
            "accessConfigs":[
               {
                  "name":"external-nat",
                  "type":"ONE_TO_ONE_NAT"
               }
            ],
            "network":"https://www.googleapis.com/compute/v1/projects/grand-sweep-254818/global/networks/default"
         }
      ],
      "scheduling":{
         "automaticRestart":True
      },
      "serviceAccounts":[
         {
            "email":"default",
            "scopes":[
            "https://www.googleapis.com/auth/cloud-platform"
            ]
         }
      ]
   }
}

regional_config = {
   "predefinedNames": names,
   "count":2,
   "instance":{
      "canIpForward":False,
      "deletionProtection":False,
      "disks":[
         {
            "autoDelete":True       ,
            "boot":True,
            "initializeParams":{
               "sourceImage":"https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/family/debian-9"
            },
            "mode":"READ_WRITE",
            "type":"PERSISTENT"
         }
      ],
      "machineType":"https://www.googleapis.com/compute/v1/projects/grand-sweep-254818/regions/{0}/machineTypes/n1-standard-1".format(region),
      "name":"unused",
      "networkInterfaces":[
         {
            "accessConfigs":[
               {
                  "name":"external-nat",
                  "type":"ONE_TO_ONE_NAT"
               }
            ],
            "network":"https://www.googleapis.com/compute/v1/projects/grand-sweep-254818/global/networks/default"
         }
      ],
      "scheduling":{
         "automaticRestart":True
      },
      "serviceAccounts":[
         {
            "email":"default",
            "scopes":[
            "https://www.googleapis.com/auth/cloud-platform"
            ]
         }
      ]
   }
}

# list instances, demonstrating how to get only the instances that bulk insert created
def list_instances(compute, project, zone, names=None):
    # filter string is of the format '(name = "instance-1") OR (name="instance-2") OR ...'
    filter_string = ""
    if names:
      filter_string = " OR ".join(['(name = "{0}")'.format(name) for name in names])

    result = compute.instances().list(
      project=project, 
      zone=zone,
      filter=filter_string
    ).execute()
    # TODO: handle pagination
    return result['items'] if 'items' in result else None

# Use BulkInsert to create instances in a particular zone 
def create_instances_in_zone(compute, project, zone, names, config):
    return compute.instances().bulkInsert(
        project=project,
        zone=zone,
        body=config
      ).execute()

# Use BulkInsert to create instances in a particular zone 
def create_instances_in_region(compute, project, region, names, config):
    return compute.regionInstances().bulkInsert(
        project=project,
        region=region,
        body=config
      ).execute()

def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        # operations.wait waits for 2 minutes and then returns whatever the current status
        result = compute.zoneOperations().wait(
            project=project,
            zone=zone,
            operation=operation
        ).execute()

        if result['status'] == 'DONE':
            return result

# get all the per-instance operations for a bulk Operation
def get_instance_operations(compute, project, zone, operation_name):
  return compute.zoneOperations().list(
    project=project,
    zone=zone,
    filter='clientOperationId = "{0}"'.format(operation_name)
  ).execute()

# get all the zones in a given region
def get_zones_in_region(compute, project, region):
  response = compute.zones().list(
    project=project,
    filter='region="https://www.googleapis.com/compute/alpha/projects/{0}/regions/{1}"'.format(project, region)
  ).execute()
  return response["items"]

# stub illustrating that you can do work on the instance
def do_work(instance_link): 
  return

# -----------------------------------------------------------
# Example 1: 
# basic example: create 2 VMs in a zone, wait for everything
# to complete, and then list all the created VMs
# also, handle any applicable errors
# -----------------------------------------------------------

def zonal_create():
  try:
    operation = create_instances_in_zone(compute, project, zone, names, zonal_config)
    result = wait_for_operation(compute, project, zone, operation['name'])
    print(result)

    # # handle operation errors
    if (result["error"]):

      # grab the first error...I guess?
      first_error = result["error"]["errors"][0]
      
      # and reason over the first error:
      if first_error["code"] == "RESOURCE_ALREADY_EXISTS":
        # handle resource collision
        print("name collision")

      elif first_error["code"] == "RESOURCE_EXHAUSTED": 
        # handle stockout 
        print("stockout")

      # etc...

    print(list_instances(compute, project, zone, names))
  
  # catch "front-end" errors
  except googleapiclient.errors.HttpError as err:
    error_content = json.loads(err.content.decode("utf-8"))
    first_error = error_content["error"]["errors"][0]

    if first_error["reason"] == "invalid":
      print("invalid request - check your JSON")  
  
    # handle the error content...
    # how would the customer know what errors could happen here?

# -----------------------------------------------------------
# Example 2: 
# basic example: create 2 VMs in a *region*, find out the
# region that was created, and then list all the created VMs
# error handling omitted for clarity...
# -----------------------------------------------------------
def regional_create():
  operation = create_instances_in_region(compute, project, region, names, regional_config)
  selected_zone = operation["metadata"]["locations"].keys()[0]    # doesn't work yet (TODO)
  wait_for_operation(compute, project, selected_zone, operation["name"])
  print(list_instances(compute, project, zone, names))


# -------------------------------------------------------------
# Example 3: 
# You want to do work on each instance the moment it is spun up
# -------------------------------------------------------------
def zonal_create_then_wait_on_instances():
  operation = create_instances_in_zone(compute)
  instance_operations = get_instance_operations(compute, project, zone, operation['name'])
  
  # probably should do this in multiple threads or something since operation.wait() is blocking...
  for instance_operation in instance_operations:
    result = wait_for_operation(compute, project, zone, instance_operation)  
    this_instance_link = result['targetLink']         
    do_work(this_instance_link)  


# -----------------------------------------------------------
# Example 4: 
# Create instances in a zone with namePattern
# -----------------------------------------------------------
def zonal_create_with_name_pattern():
  # modify our zonal config to use name pattern
  nVMs = 2                                        # instances to create
  zonal_config["predefinedNames"]
  zonal_config["namePattern"] = "instance-####"
  zonal_config["count"] = nVMs
  operation = create_instances_in_zone(compute, project, zone, None, config)

  # At this point, to get the VMs, you could list the per-instance operations as in example 3
  # Or, you can use the following logic to infer which VMs were created:
  vm_names = []
  idx = int(operation["metadata"]["startingIndex"])     # the index of the first VM created
  while (nVMs > 0):
    vm_names.append("instance-{:03d}".format(idx))      
    idx += 1
    nVms -= 1

# -----------------------------------------------------------
# Example 5: 
# Get me 1000 VMs - they can be spread out across the zones
# in this region
# -----------------------------------------------------------
def region_create_spread_okay():
  nVMs = 1000
  zonal_config["predefinedNames"]
  zonal_config["namePattern"] = "instance-####"
  zonal_config["count"] = nVMs
  zonal_config["minCount"] = 0      # minCount = 0 is equivalent to: create as many as you can

  zones = get_zones_in_region(compute, project, region)
  zone_names = [zone["name"] for zone in zones]
  for zone in zone_names:
    operation = create_instances_in_zone(compute, project, zone, names, zonal_config)
    wait_for_operation(compute, project, selected_zone, operation["name"])
    nCreated = operation["metadata"]["instancesCreated"]
    nVMs -= nCreated
    if (nVMs == 0):
      break

# -----------------------------------------------------------
# Example 6: 
# I need 1000 VMs - 
# they can be C2, N2, N1 or E2
# they need to be in the same zone
# they need to be homogenous 
# Could also use this approach to try different regions
# -----------------------------------------------------------
def try_different_machine_families():
  nVMs = 1000
  acceptable_families = ["c2", "n2", "n1", "e2"] 
  region = "us-central1"

  for family in acceptable_families:
    try:
      regional_config["machineType"] = "https://www.googleapis.com/compute/v1/projects/grand-sweep-254818/regions/{0}/machineTypes/{1}-standard-1".format(region, family)
      operation = create_instances_in_region(compute, project, zone, names, zonal_config)
      result = wait_for_operation(compute, project, zone, operation['name'])

      # # handle operation errors
      if (!result["error"]):        
        print(list_instances(compute, project, zone, names))
        break

      # error handling...
      else:
        print("something went wrong")
        # error handling...
    
    # catch the frontend will tell you about stockouts
    except googleapiclient.errors.HttpError as err:
      error_content = json.loads(err.content.decode("utf-8"))
      first_error = error_content["error"]["errors"][0]

      # if stockout, then just keep trying machien types
      if first_error["reason"] == "RESOURCE_EXHAUSTED":
        continue

# -----------------------------------------------------------
# Example 7: 
# Get me more than 1000 VMs, all in the same zone
# -----------------------------------------------------------
# TODO



