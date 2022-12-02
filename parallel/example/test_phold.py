from mpi4py import MPI
from numpy.random import seed

from psequence.phold import PholdNode
from psequence.p_timeline import ParallelTimeline


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('total_node', type=int)
    parser.add_argument('init_work', type=int)
    parser.add_argument('lookahead', type=int)
    parser.add_argument('stop_time', type=int)

    args = parser.parse_args()

    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()
    seed(rank)

    node_num = args.total_node // size
    timeline = ParallelTimeline(args.lookahead, args.stop_time)
    neighbors = list(range(args.total_node))
    neighbors = list(map(str, neighbors))
    for i in range(args.total_node):
        if i // node_num == rank:
            node = PholdNode(str(i), timeline, args.init_work // args.total_node, args.lookahead, neighbors)
        else:
            timeline.foreign_entities[str(i)] = i // node_num

    timeline.init()
    timeline.run()
    print(timeline.id, timeline.now(), timeline.events.top().time, timeline.sync_counter, timeline.run_counter,
          sum([len(buf) for buf in timeline.event_buffer]), len(timeline.events))
