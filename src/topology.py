import json

class ezFormat:
    dict = {}
    def __init__(self,filename):
        with open(filename) as f:
            for line in f:
                if not line:
                    break
                if line.startswith('#'):
                    continue
                tokens = line.split()
                if len(tokens)>1:
                    if len(tokens)==2:
                        self.dict[tokens[0]] = tokens[1]
                    else:
                        self.dict[tokens[0]] = tokens[1:]

    def get_dict(self):
        return self.dict


class NodeClass():
    nodeID = -1
    nodeName = ""
    components = []
    
    def setNodeID(self,id):
        self.nodeID = id

    def setNodeName(self,name):
        self.nodeName = name

    def setNodeComponents(self,components):
        self.components = components

    def addComponent(self,component):
        self.components.append(component)


class Topology():
    topology = ""
    num_nodes = 0
    nodes = []

    def get_token(self,line,ind=-1):
        tokens = line.split()
        return tokens[ind]

    def get_list(self,line):
        tokens = line.split()
        if len(tokens)>1:
            return tokens[1:]
        return []

    def parse_node_dict(self,dict):
        node = NodeClass()
        for k in dict.keys():
            if k=="nodeID":
                node.setNodeID(dict[k])
            elif k=="nodeName":
                node.setNodeName(dict[k])
            elif k=="components":
                node.setNodeComponents(dict[k])
        return node

    def read_node(self,filename):
        ez = ezFormat(filename)
        dict = ez.get_dict()
        node = self.parse_node_dict(dict)
        return node

    def read_topology(self,topologyfile):
        print ("topology file:",topologyfile)
        with open(topologyfile) as fp:  
            while True:
                line = fp.readline().strip()
                #print (line)
                if not line:
                    break
                if line.startswith('#'):
                    continue
                if line.startswith('topology:'):
                    self.topology = self.get_token(line)
                elif line.startswith('nodefiles:'):
                    self.nodefiles = self.get_list(line)
                    for fn in self.nodefiles:
                        node = self.read_node(fn)
                        self.nodes.append(node)
                        self.num_nodes += 1

    def print_topology(self):
        print ("topology:",self.topology)
        print ("num_nodes:",self.num_nodes)
        print ("nodes:",self.nodes)
