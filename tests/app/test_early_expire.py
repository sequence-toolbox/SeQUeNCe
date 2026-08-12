from collections import defaultdict
from sequence.topology.node import QuantumRouter
from sequence.app.request_app import RequestApp
from sequence.network_management.reservation import Reservation
from sequence.constants import MILLISECOND, SECOND
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.resource_management.memory_manager import MemoryInfo
from sequence.utils.graphs import build_linear
from sequence.utils.nx_converter import generate_config
from sequence.topology.router_net_topo import RouterNetTopo



def test_EarlyExpire():

    REQUEST_DURATION = 2 * SECOND          # difference between start and end time of a request
    PATHFINDING_DURATION = 5 * MILLISECOND # time for path finding and reservation setup

    # needs a custom app that overrides the get_memory method to expire the rules before the end time of the reservation
    class RequestAppEarlyExpire(RequestApp):

        def __init__(self, node: QuantumRouter):
            super().__init__(node)
            self.entanglement_timestamps = defaultdict(list)  # reservation: list[float]
            self.entanglement_number = 1
            self.request_success_counter = 0
            self.request_failure_counter = 0
            self.reservation_to_scheduled_event = {}  # reservation -> event for removing memo reservation map at the end time of the reservation

        def get_reservation_result(self, reservation: Reservation, result: bool) -> None:
            """Method to receive reservation result from network manager. 

            The initiator will call this method once received a response from the responder.

            Args:
                reservation (Reservation): reservation that has been completed.
                result (bool): result of the request (approved/rejected).

            Side Effects:
                May schedule a start/retry event based on reservation result.
            """
            super().get_reservation_result(reservation, result)
            if result:
                self.request_success_counter += 1
            else:
                self.request_failure_counter += 1

        def start_request_schedule_next(self, responder: str, start_t: int, end_t: int, memo_size: int, fidelity: float, entanglement_number: int = 1, id: int = 0):
            '''Start the request and schedule the next request after 1 second, i.e., 1 request per second

            Args:
                responder: the destination of the request
                start_t: the start time of the request
                end_t: the end time of the request
                memo_size: the memory size of the request
                fidelity: the fidelity requirement of the request
                entanglement_number: the number of entanglement pairs requested
                id: the id of the request
            '''
            # start the request
            self.start(responder, start_t, end_t, memo_size, fidelity, entanglement_number, id)
            # schedule the next request in 1 second
            event_t = self.node.timeline.now() + 1 * SECOND
            start_t = event_t + PATHFINDING_DURATION # for path finding and reservation setup
            end_t = start_t + REQUEST_DURATION
            process = Process(self, "start_request_schedule_next", [responder, start_t, end_t, memo_size, fidelity, entanglement_number, id+1])
            event = Event(event_t, process)
            self.node.timeline.schedule(event)

        def start(self, responder: str, start_t: int, end_t: int, memo_size: int, fidelity: float, entanglement_number: int = 1, id: int = 0):
            """Method to start the application.

                This method will use arguments to create a request and send to the network.

            Side Effects:
                Will create request for network manager on node.
            """
            assert 0 < fidelity <= 1
            assert 0 <= start_t <= end_t
            assert 0 < memo_size
            self.responder = responder
            self.start_t = start_t
            self.end_t = end_t
            self.memo_size = memo_size
            self.fidelity = fidelity
            self.entanglement_number = entanglement_number
            self.id = id

            self.node.reserve_net_resource(responder, start_t, end_t, memo_size, fidelity, entanglement_number, id)

        def get_memory(self, info: "MemoryInfo") -> None:
            """Method to receive entangled memories.

            Will check if the received memory is qualified.
            If it's a qualified memory, the application sets memory to RAW state
            and release back to resource manager.
            The counter of entanglement memories, 'memory_counter', is added.
            Otherwise, the application does not modify the state of memory and
            release back to the resource manager.

            Args:
                info (MemoryInfo): info on the qualified entangled memory.
            """

            if info.state != "ENTANGLED":
                return

            if info.index in self.memo_to_reservation:
                reservation = self.memo_to_reservation[info.index]
                if info.remote_node == reservation.initiator:  # the responder
                    if info.fidelity >= reservation.fidelity:
                        self.entanglement_timestamps[reservation].append(self.node.timeline.now())
                        self.node.resource_manager.update(None, info.memory, MemoryInfo.RAW)
                        entanglement_number = len(self.entanglement_timestamps[reservation])
                        if entanglement_number == reservation.entanglement_number:
                            self.node.resource_manager.expire_rules_by_reservation(reservation)
                            self.node.network_manager.remove_reservation_from_timecards(reservation)
                            self.remove_memo_reservation_map(info.index)
                            self.reservation_to_scheduled_event[reservation].set_invalid()

                elif info.remote_node == reservation.responder:  # the initiator
                    if info.fidelity >= reservation.fidelity:
                        self.entanglement_timestamps[reservation].append(self.node.timeline.now())
                        entanglement_number = len(self.entanglement_timestamps[reservation])
                        self.node.resource_manager.update(None, info.memory, MemoryInfo.RAW)

                        if entanglement_number == reservation.entanglement_number:
                            self.node.resource_manager.expire_rules_by_reservation(reservation)
                            self.node.network_manager.remove_reservation_from_timecards(reservation)
                            self.remove_memo_reservation_map(info.index)
                            self.reservation_to_scheduled_event[reservation].set_invalid()
                            self.send_expire_rules_message(reservation)

        def send_expire_rules_message(self, reservation: Reservation):
            '''send the expire rule message to nodes other than the initiator and responder

            Args:
                reservation: the rules to expires is generated for this reservation
            '''
            path = reservation.path
            if len(path) > 2:
                for i in range(1, len(path) - 1):
                    node = path[i]
                    self.node.resource_manager.expire_remote_rules(node, reservation)

        def schedule_reservation(self, reservation: Reservation) -> None:
            """Calling the `add_memo_reservation_map` and `remove_memo_reservation_map` methods at the 
            reservation's start_time and end_time for all timecards (memory) involved in the reservation. 
            
            Called by the initiator and the responder when reservation is approved.

            Args:
                reservation (Reservation): reservation to schedule
            """
            if reservation.initiator == self.node.name:
                self.path = reservation.path

            for card in self.node.network_manager.get_timecards():
                if reservation in card.reservations:
                    process = Process(self, "add_memo_reservation_map", [card.memory_index, reservation])
                    event = Event(reservation.start_time, process)
                    self.node.timeline.schedule(event)
                    process = Process(self, "remove_memo_reservation_map", [card.memory_index])
                    event = Event(reservation.end_time, process)
                    self.node.timeline.schedule(event)
                    self.reservation_to_scheduled_event[reservation] = event


    node_template = {
        "router_template": {
            "MemoryArray": {
                "efficiency": 0.9
            }
        },
        "bsm_template": {
            "encoding_type": "single_atom",
        }
    }

    # 3-node linear topology, 2 memories per node, 2 seconds simulation time
    graph = build_linear(3)
    config, _ = generate_config(graph, cc_delay=0.1, memory_size=2, stop_time=2, node_template=node_template)
    topo = RouterNetTopo(config)
    tl = topo.get_timeline()
    
    name_to_app = {}
    for router in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        name_to_app[router.name] = RequestAppEarlyExpire(router)

    tl.init()
    app: RequestAppEarlyExpire = name_to_app["router_0"]
    start_t = PATHFINDING_DURATION
    end_t   = start_t + REQUEST_DURATION
    app.start_request_schedule_next(responder = "router_2", start_t=start_t, end_t=end_t, memo_size=1, fidelity=0.1, entanglement_number=1, id=0)
    tl.run()

    # Two requests
    # First request:  [0,2] seconds
    # Second request: [1,3] seconds
    # Without early expire,  the second request fails
    # But with early expire, the second request succeeds
    assert app.request_success_counter == 2
    assert app.request_failure_counter == 0
    assert len(app.entanglement_timestamps) == 2
