# Topology Extension Examples

These examples show three different extension levels for the refactored topology layer.

## 1. Custom node only

File: `custom_router_node.py`

Use this pattern when an existing topology family already does the right network construction,
and you only need a custom node type with extra state, hardware, or behavior.

Workflow:
- subclass a compatible built-in node such as `QuantumRouter` or `BSMNode`
- register it with `@Node.register("YourNodeType")`
- use that custom type name directly in config

Example fit:
- `YbRouterNode`
- `ErRouterNode`
- router subclasses with custom applications, hardware labels, or manager wiring

## 2. Registry pipeline + custom from_config

File: `registry_pipeline_demo.py`

Use this pattern when you want to load an existing config file and customize
the build at runtime — override parameters, extend the node list, or add connections.

Workflow:
- define a custom node with a `from_config` classmethod for config-driven construction
- pass a file path to a topology constructor
- use kwargs to override scalars (`stop_time`), extend lists (`nodes`, `qconnections`), or merge dicts
- inspect results with `get_nodes_by_type`

Example fit:
- parameter sweeps over a base config
- extending a config with extra nodes or connections at runtime
- custom nodes that need non-trivial construction from config fields

## 3. Custom node + custom topology-family hook

File: `heterogeneous_midpoints.py`

Use this pattern when custom node types are not enough, and the topology family must generate
or wire the network differently.

Workflow:
- define custom node types as above
- subclass the relevant topology family, such as `BsmTopologyFamily`
- override only the hook that needs family-specific behavior
- keep the shared `Topology` build pipeline intact

Example fit:
- custom midpoint nodes such as `QFCBSMNode`
- connection-dependent hardware insertion
- heterogeneous platform handling based on endpoint properties

## Rule of thumb

Start with a custom node type.

Only subclass a topology family when the topology must:
- generate different infrastructure
- wire nodes/channels differently
- attach different family-specific protocols during the build
