# Fabric Crossconnect Service

The Fabric Crossconnect service creates an L2 bridge between two given ports on the same device. For example, this service can be used on a SEBA pod to connect OLT devices to a BNG via the aggregation switch.

A fabric crossconnect entry is a tuple (`deviceid`, `vlanid`, `port1`, `port2`).

For more information, see [VLAN Cross Connect](https://wiki.opencord.org/display/CORD/VLAN+Cross+Connect)

## Models

This service is comprised of three models:

- `FabricCrossconnectService` global service-related parameters, such as the name of the service. There is currently no additional state here beyond the default `XOS` `Service` model.
- `FabricCrossconnectServiceInstance` represents one half of a vlan crossconnect. Fields include the following:
	- `s-tag` the vlan_id that will be connected
	- `switch_datapath_id` switch id where the vlan crossconnect will be enacted
	- `source_port` port number on the switch
- `BNGPortMapping` represents the other half of a vlan crossconnect. Fields include the following:
	- `s_tag` the vlan_id that will be connected. In addition to specifying a single vlan_id, the keyword `ANY` may be used, or a range (`123-456`) may be used.
	- `switch_port` port number on the switch

`FabricCrossconnectServiceInstance` and `BNGPortMapping` work together to create the vlan crossconnect tuple, linked by a common `s-tag`.

### Example TOSCA

Below is an example TOSCA recipe that creates a `FabricCrossconnectServiceInstance`:

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/fabriccrossconnectservice.yaml
  - custom_types/fabriccrossconnectserviceinstance.yaml
description: Create a FabricCrossconnectServiceInstance
topology_template:
  node_templates:
    service#fabric-crossconnect:
      type: tosca.nodes.FabricCrossconnectService
      properties:
        name: fabric-crossconnect
        must-exist: true

    fcsi:
      type: tosca.nodes.FabricCrossconnectServiceInstance
      properties:
        name: "custom_vm_crossconnect"
        s_tag: 123
        source_port: 3
        switch_datapath_id: "of:0000000000000201"
      requirements:
        - owner:
            node: service#fabric-crossconnect
            relationship: tosca.relationships.BelongsToOne
```

Below is an example TOSCA recipe that creates a `BNGPortMapping` for a single s-tag:

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/bngportmapping.yaml
description: Create a bng port mapping
topology_template:
  node_templates:
    bngmapping:
      type: tosca.nodes.BNGPortMapping
      properties:
        s_tag: "222"
        switch_port: 4
```

## Integration with other Services

The western neighbor of the `FabricCrossconnectService` is typically an access service such as `VOLTService`. `FabricCrossconnectServiceInstance` participates in the dataplane chain for a given subscriber.

`FabricCrossConnectService` features a method `acquire_service_instance(subscriber_service_instance)` that may be used as a helper for creating service instances. Given that many subscribers may map to a single `s_tag`, it's often the case that a single `FabricCrossconnectServiceInstance` is used by several subscribers. `acquire_service_instance` does the following:

1) Check to see if an eligible `FabricCrossconnnectServiceInstance` already exists, and if so links it to the subscriber_service_instance.
2) If no eligible `FabricCrossconnectServiceInstance` already exists, then a new one will be created and linked.

## Synchronization workflow

### FabricCrossconnectServiceInstance

When a `FabricCrossconnectServiceInstance` is created, updated, or deleted, the synchronizer will make a REST API call to ONOS.

### BNGPortMapping

No specific processing is performed if a `BNGPortMapping` is created, updated, or deleted, as the workflow is driven by `FabricCrossconnectServiceInstance`. Responding to changes in `BNGPortMapping` is future work. For now it is suggested that if you need to change one, afterward you touch any `FabricCrossconnectServiceInstance` that may be affected, causing them to resynchronize.
 