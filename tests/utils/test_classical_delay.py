from sequence.utils.classical_delay import update_cchannel_delay
from sequence.utils.config_generator_cli import generate_config, build_linear
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import MICROSECOND, MILLISECOND


def test_update_cchannel_delay():
    # linear topology: 0 -- 1 -- 2
    g = build_linear(3, length=10.0, attenuation=0.0002)
    config, graph_to_name = generate_config(g, cc_delay=1, output_file=None, output_directory=None)
    topo = RouterNetTopo(config)
    r0 = graph_to_name[0]
    r1 = graph_to_name[1]
    r2 = graph_to_name[2]
    cc_01_name = f"cc-{r0}-{r1}"
    cc_02_name = f"cc-{r0}-{r2}"
    cc_12_name = f"cc-{r1}-{r2}"
    cc_01 = topo.tl.get_entity_by_name(cc_01_name)
    cc_02 = topo.tl.get_entity_by_name(cc_02_name)
    cc_12 = topo.tl.get_entity_by_name(cc_12_name)

    # before update: every classical channel has a delay of 1 millisecond
    assert cc_01.delay == cc_02.delay == cc_12.delay == 1 * MILLISECOND

    update_cchannel_delay(topo, classical_delay_node=100, classical_delay_hop=20)

    # after update: the classical channel delay varies based on the distance and hop count
    assert cc_01.delay == cc_12.delay == 150 * MICROSECOND # 50 + 100
    assert cc_02.delay == 220 * MICROSECOND # 100 + 20 + 100
