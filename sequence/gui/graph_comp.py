"""
Basic graph node component
"""


class GraphNode:
    def __init__(self, node_name, node_type, template):
        self.name = node_name
        self.type = node_type
        self.template = template
