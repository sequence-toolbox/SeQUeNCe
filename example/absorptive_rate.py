from absorptive_experiment import *
from matplotlib import pyplot as plt

num = 4
mean_num_list = np.linspace(0.02, 0.05, num=num, endpoint=True)
mode_num_list = np.arange(10, 105, step=5)
rate_list = []

for mean_num in mean_num_list:
    mean_num_list = []

    for mode_num in mode_num_list:
        tl = Timeline(time, formalism=FOCK_DENSITY_MATRIX_FORMALISM, truncation=TRUNCATION)

        anl_name = "Argonne"
        hc_name = "Harper Court"
        erc_name = "Eckhardt Research Center BSM"
        erc_2_name = "Eckhardt Research Center Measurement"
        seeds = [1, 2, 3, 4]
        src_list = [anl_name, hc_name]  # the list of sources, note the order

        anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, mean_photon_num=mean_num,
                      spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY1, abs_effi=ABS_EFFICIENCY1,
                      afc_efficiency=efficiency1, mode_number=mode_num)
        hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, mean_photon_num=mean_num,
                     spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY2, abs_effi=ABS_EFFICIENCY2,
                     afc_efficiency=efficiency2, mode_number=mode_num)
        erc = EntangleNode(erc_name, tl, src_list)
        erc_2 = MeasureNode(erc_2_name, tl, src_list)

        for seed, node in zip(seeds, [anl, hc, erc, erc_2]):
            node.set_seed(seed)

        # extend fiber lengths to be equivalent
        fiber_length = max(DIST_ANL_ERC, DIST_HC_ERC)

        qc1 = add_channel(anl, erc, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
        qc2 = add_channel(hc, erc, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
        qc3 = add_channel(anl, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
        qc4 = add_channel(hc, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)

        tl.init()

        # Pre-simulation explicit calculation of entanglement fidelity upon successful BSM

        # use non-transmitted Photon as interface with existing methods in SeQUeNCe
        spdc_anl = anl.components[anl.spdc_name]
        spdc_hc = hc.components[hc.spdc_name]
        memo_anl = anl.components[anl.memo_name]
        memo_hc = hc.components[hc.memo_name]
        channel_anl = anl.qchannels[erc_name]
        channel_hc = hc.qchannels[erc_name]
        bsm = erc.components[erc.bsm_name]

        # photon0: idler, photon1: signal
        photon0_anl = Photon("", spdc_anl.timeline, wavelength=spdc_anl.wavelengths[0], location=spdc_anl,
                             encoding_type=spdc_anl.encoding_type, use_qm=True)
        photon1_anl = Photon("", spdc_anl.timeline, wavelength=spdc_anl.wavelengths[1], location=spdc_anl,
                             encoding_type=spdc_anl.encoding_type, use_qm=True)
        # set shared state to squeezed state
        state_spdc_anl = spdc_anl._generate_tmsv_state()
        keys = [photon0_anl.quantum_state, photon1_anl.quantum_state]
        tl.quantum_manager.set(keys, state_spdc_anl)

        photon0_hc = Photon("", spdc_hc.timeline, wavelength=spdc_hc.wavelengths[0], location=spdc_hc,
                            encoding_type=spdc_hc.encoding_type, use_qm=True)
        photon1_hc = Photon("", spdc_hc.timeline, wavelength=spdc_hc.wavelengths[1], location=spdc_hc,
                            encoding_type=spdc_hc.encoding_type, use_qm=True)
        # set shared state to squeezed state
        state_spdc_hc = spdc_hc._generate_tmsv_state()
        keys = [photon0_hc.quantum_state, photon1_hc.quantum_state]
        tl.quantum_manager.set(keys, state_spdc_hc)

        # photon loss upon absorption by memories
        key_anl_memo = photon1_anl.quantum_state
        loss_anl_memo = 1 - memo_anl.absorption_efficiency
        tl.quantum_manager.add_loss(key_anl_memo, loss_anl_memo)
        key_hc_memo = photon1_hc.quantum_state
        loss_hc_memo = 1 - memo_hc.absorption_efficiency
        tl.quantum_manager.add_loss(key_hc_memo, loss_hc_memo)

        # transmission loss through optical fibres (overwrites previous variables)
        key_anl_pho = photon0_anl.quantum_state
        loss_anl_pho = channel_anl.loss
        tl.quantum_manager.add_loss(key_anl_pho, loss_anl_pho)
        key_hc_pho = photon0_hc.quantum_state
        loss_hc_pho = channel_anl.loss
        tl.quantum_manager.add_loss(key_hc_pho, loss_hc_pho)

        # QSDetector measurement and remaining state after partial trace
        povms = bsm.povms
        povm_tuple = tuple([tuple(map(tuple, povm)) for povm in povms])
        keys = [photon0_anl.quantum_state, photon0_hc.quantum_state]
        new_state, all_keys = tl.quantum_manager._prepare_state(keys)
        indices = tuple([all_keys.index(key) for key in keys])
        state_tuple = tuple(map(tuple, new_state))
        states, probs = measure_multiple_with_cache_fock_density(state_tuple, indices, len(all_keys), povm_tuple,
                                                                 tl.quantum_manager.truncation)

        # Pre-simulation explicit calculation of entanglement generation rate based on calculation above

        duration_photon = mode_num / SPDC_FREQUENCY * 1e12  # duration of emitted photon train from SPDC source
        delay_fiber_anl = anl.qchannels[erc_name].delay
        delay_fiber_hc = hc.qchannels[erc_name].delay
        assert delay_fiber_anl == delay_fiber_hc
        delay_fiber = delay_fiber_anl  # time for photon to travel from SPDC source to BSM device
        delay_classical = DELAY_CLASSICAL * 1e12  # delay for classical communication between BSM node and memory nodes

        # total duration from first photon emitted to last photon's detection result communicated back
        duration_tot = duration_photon + delay_fiber + delay_classical

        prob_herald = probs[1] + probs[2]  # calculate heralding probability
        num_generated_avg = mode_num * prob_herald  # average number of entangled pairs generated in one emission cycle

        rate = num_generated_avg / duration_tot * 1e12

        mean_num_list.append(rate)
    rate_list.append(mean_num_list)

"""Store results"""

# open file to store experiment results
Path("results").mkdir(parents=True, exist_ok=True)
filename = "results/absorptive_rate.json"
fh = open(filename, 'w')
info = {"rate_list": rate_list}
dump(info, fh)

list1, list2, list3, list4 = rate_list
fig = plt.figure(figsize=(8, 6))
plt.plot(mode_num_list, list1, label='$\mu=0.02$')
plt.plot(mode_num_list, list2, label='$\mu=0.03$')
plt.plot(mode_num_list, list3, label='$\mu=0.04$')
plt.plot(mode_num_list, list4, label='$\mu=0.05$')
plt.title("Entanglement Generation Rate with Mode Number")
plt.xlabel("mode number $M$")
plt.ylabel("entanglement generation rate $R$ (Hz)")
plt.legend()
plt.show()
