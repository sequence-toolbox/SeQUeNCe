from sequence.topology.qlan.orchestrator import QlanOrchestratorNode
from sequence.topology.qlan.client import QlanClientNode
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import ClassicalChannel
from sequence.qlan.measurement import QlanMeasurementMsgType, QlanB0MsgType

def pair_protocol(orchestrator: QlanOrchestratorNode, clients: list[QlanClientNode]):
    
    p_orch = orchestrator.protocols[0]
    orch_memo_name1 = orchestrator.resource_manager.memory_names[0]
    protocols_names = []
    clients_names = []
    clients_memory_names = []
    
    for client in clients:
        p_client = client.protocols[0]
        protocols_names.append(p_client)
        clients_names.append(client.name)
        clients_memory_names.append(client.resource_manager.memory_names[0])

        p_client.set_others(p_orch.name, orchestrator.name, [orch_memo_name1])

    p_orch.set_others(protocols_names, clients_names, [orch_memo_name1])


def test_send_ack_messages_z_0():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(2)
    test_orch.update_bases('z')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.Z_Outcome0
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.Z_Outcome0
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0

def test_send_ack_messages_z_1():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(0)
    test_orch.update_bases('z')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.Z_Outcome1
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.Z_Outcome1
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1


def test_send_ack_messages_y_0():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(2)
    test_orch.update_bases('y')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.Y_Outcome0
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.Y_Outcome0
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0

def test_send_ack_messages_y_1():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(0)
    test_orch.update_bases('y')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.Y_Outcome1
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.Y_Outcome1
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1

def test_send_ack_messages_x_0():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(2)
    test_orch.update_bases('x')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.X_Outcome0 or test_client1.protocols[0].received_messages[i] is QlanB0MsgType.B0
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.X_Outcome0 or test_client2.protocols[0].received_messages[i] is QlanB0MsgType.B0
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome0

def test_send_ack_messages_x_1():
    tl = Timeline()

    test_client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    test_client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)

    test_memo1 = test_client1.get_components_by_type("Memory")[0]
    test_memo2 = test_client2.get_components_by_type("Memory")[0]

    test_orch = QlanOrchestratorNode("test_orch", tl, num_local_memories=1, remote_memories=[test_memo1, test_memo2])
    test_orch.set_seed(0)
    test_orch.update_bases('x')
    
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c1.set_ends(test_orch, test_client1.name)
    cc_o_c2.set_ends(test_orch, test_client2.name)

    cc_c1_o = ClassicalChannel("cc_c_o1", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c1_o.set_ends(test_client1, test_orch.name)
    cc_c2_o.set_ends(test_client2, test_orch.name)

    test_orch.resource_manager.create_protocol()
    test_client1.resource_manager.create_protocol()
    test_client2.resource_manager.create_protocol()

    tl.init()

    pair_protocol(orchestrator=test_orch, clients=[test_client1, test_client2])

    test_client1.protocols[0].start()
    test_client2.protocols[0].start()
    test_orch.protocols[0].start(test_orch)

    for i in range(len(test_client1.protocols[0].received_messages)):
        assert test_client1.protocols[0].received_messages[i] is QlanMeasurementMsgType.X_Outcome1 or test_client1.protocols[0].received_messages[i] is QlanB0MsgType.B0
        assert test_client1.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1
    
    for i in range(len(test_client2.protocols[0].received_messages)):
        assert test_client2.protocols[0].received_messages[i] is QlanMeasurementMsgType.X_Outcome1 or test_client2.protocols[0].received_messages[i] is QlanB0MsgType.B0
        assert test_client2.protocols[0].sent_messages[i] is QlanMeasurementMsgType.ACK_Outcome1
