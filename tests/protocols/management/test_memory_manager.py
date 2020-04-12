from sequence.protocols.management.memory_manager import *
from sequence.kernel.timeline import Timeline
from sequence.components.memory import *


def test_update():
    tl = Timeline()
    arr = MemoryArray("memo_arr", tl)
    memo = arr[0]
    memo.fidelity = 0.6
    memo.entangled_memory = {"node_id": "alice", "memo_id": 0}

    manager = MemoryManager(arr)
    manager.update(memo, "ENTANGLED")

    assert manager[0].state == "ENTANGLED"
    assert manager[0].fidelity == 0.6
    assert manager[0].remote_node == "alice"
    assert manager[0].remote_memo == 0


