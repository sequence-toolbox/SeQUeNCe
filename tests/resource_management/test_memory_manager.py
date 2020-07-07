from sequence.resource_management.memory_manager import *
from sequence.kernel.timeline import Timeline
from sequence.components.memory import *


def test_update():
    tl = Timeline()
    arr = MemoryArray("memo_arr", tl)
    memo = arr[0]
    manager = MemoryManager(arr)

    # Test RAW

    manager.update(memo, "RAW")

    assert manager[0].state == "RAW"
    assert manager[0].fidelity == 0
    assert manager[0].remote_node == None
    assert manager[0].remote_memo == None

    # Test OCCUPIED

    manager.update(memo, "OCCUPIED")

    # should not change
    assert manager[0].state == "OCCUPIED"
    assert manager[0].fidelity == 0
    assert manager[0].remote_node == None
    assert manager[0].remote_memo == None

    # Test ENTANGLED

    memo.fidelity = 0.6
    memo.entangled_memory = {"node_id": "alice", "memo_id": 0}

    manager.update(memo, "ENTANGLED")

    assert manager[0].state == "ENTANGLED"
    assert manager[0].fidelity == 0.6
    assert manager[0].remote_node == "alice"
    assert manager[0].remote_memo == 0


