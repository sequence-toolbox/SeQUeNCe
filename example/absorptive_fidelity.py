from absorptive_experiment import *
from json import JSONEncoder
from matplotlib import pyplot as plt

dim = 100
mean_num1_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)
mean_num2_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)
fidelity_mat = np.zeros((dim, dim))


# effective Bell state generated
def effective_state(state):
    state[0][0] = 0
    state = state / np.trace(state)
    return state


# for storage
class NumpyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


for idx1, mean_num1 in enumerate(mean_num1_list):
    for idx2, mean_num2 in enumerate(mean_num2_list):

        tl = Timeline(time, formalism=FOCK_DENSITY_MATRIX_FORMALISM, truncation=TRUNCATION)

        anl_name = "Argonne"
        hc_name = "Harper Court"
        erc_name = "Eckhardt Research Center BSM"
        erc_2_name = "Eckhardt Research Center Measurement"
        seeds = [1, 2, 3, 4]
        src_list = [anl_name, hc_name]  # the list of sources, note the order

        anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, mean_photon_num=mean_num1,
                      spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY1, abs_effi=ABS_EFFICIENCY1,
                      afc_efficiency=efficiency1, mode_number=MODE_NUM)
        hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, mean_photon_num=mean_num2,
                     spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY2, abs_effi=ABS_EFFICIENCY2,
                     afc_efficiency=efficiency2, mode_number=MODE_NUM)
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
        state_plus, state_minus = states[1], states[2]

        indices = tuple([all_keys.index(key) for key in keys])
        new_state_tuple = tuple(map(tuple, state_plus))
        remaining_state = density_partial_trace(new_state_tuple, indices, len(all_keys),
                                                tl.quantum_manager.truncation)


        remaining_state_eff = effective_state(remaining_state)

        # calculate the fidelity with reference Bell state
        bell_plus = build_bell_state(tl.quantum_manager.truncation, "plus")
        bell_minus = build_bell_state(tl.quantum_manager.truncation, "minus")
        fidelity = np.trace(remaining_state_eff.dot(bell_minus)).real

        fidelity_mat[idx1][idx2] = fidelity

    print("finished mean num {} out of {}".format(idx1 + 1, dim))

"""Store results"""

# open file to store experiment results
Path("results").mkdir(parents=True, exist_ok=True)
filename = "results/absorptive_fidelity.json"
fh = open(filename, 'w')
info = {"fidelity matrix": fidelity_mat}
dump(info, fh, cls=NumpyEncoder)

# plot the 2-d matrix
num1, num2 = np.meshgrid(mean_num1_list, mean_num2_list)
fig = plt.figure(figsize=(8, 6))
im = plt.imshow(fidelity_mat, cmap=plt.cm.RdBu, extent=(0.02, 0.1, 0.1, 0.02))
plt.colorbar(im)
plt.title("Effective Fidelity with Mean Photon Number")
plt.xlabel("mean photon number of source 1 $\mu_1$")
plt.ylabel("mean photon number of source 2 $\mu_2$")
plt.show()
