from sys import argv
from mpi4py import MPI
from numpy.random import seed

from sequence.kernel.p_timeline import ParallelTimeline
from sequence.utils.phold import PholdNode


if __name__ == '__main__':
    total_node = int(argv[1])
    init_work = int(argv[2])
    lookahead = int(argv[3])
    stop_time = int(argv[4])

    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()
    seed(rank)

    node_num = total_node // size
    timeline = ParallelTimeline(lookahead, stop_time)
    neighbors = list(range(total_node))
    neighbors = list(map(str, neighbors))
    for i in range(total_node):
        if i // node_num == rank:
            node = PholdNode(str(i), timeline, init_work // total_node, lookahead, neighbors)
        else:
            timeline.foreign_entities[str(i)] = i // node_num

    timeline.init()
    timeline.run()
    print(timeline.id, timeline.now(), timeline.events.top().time, timeline.sync_counter, timeline.event_counter, sum([len(buf) for buf in timeline.event_buffer]), len(timeline.events))

