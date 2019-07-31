import topology
from timeline import Timeline

if __name__ == "__main__":
    tl = Timeline(1e12)

    qc_ac = topology.QuantumChannel("qc_ac", tl)
    qc_bc = topology.QuantumChannel("qc_bc", tl)
    cc_ac = topology.ClassicalChannel("cc_ac", tl)
    cc_bc = topology.ClassicalChannel("cc_bc", tl)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl)
    components = {"lightsource": ls}

    alice = topology.Node("alice", tl, components=components)

    # Bob
    spdc = topology.SPDCSource("bob.lightsource", tl)
    detector = topology.Detector(tl)
    components = {"lightsource": spdc, "detector": detector}

    bob = topology.Node("bob", tl, components=components)

    # Charlie
    bsm = topology.BSM("charlie.bsm", tl)
    components = {"bsm": bsm}
    charlie = topology.Node("charlie", tl, components=components)

    pass
