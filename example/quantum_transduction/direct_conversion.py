"""Quantum transduction via direct conversion

NOTE: Work in progress
"""
import numpy as np
import matplotlib.pyplot as plt

from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.topology.node import Node
from sequence.components.photon import Photon
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.transmon import Transmon
from sequence.components.transducer import Transducer
from sequence.components.detector import FockDetector
from sequence.constants import KET0, KET1

import sys
sys.path.append('.')
from example.quantum_transduction.conversion_protocols import (
    EmittingProtocol, UpConversionProtocol, DownConversionProtocol)



# GENERAL

NUM_TRIALS = 50
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308  # nm
OPTICAL_WAVELENGTH = 1550  # nm

# Timeline
START_TIME = 0
EMISSION_DURATION = 10  # ps
CONVERSION_DURATION = 10  # ps
PERIOD = EMISSION_DURATION + CONVERSION_DURATION + CONVERSION_DURATION


state_list = [KET1, KET0]
TRANSMON_EFFICIENCY = 1

# Transducer
EFFICIENCY_UP = 0.6
EFFICIENCY_DOWN = 0.6

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3


class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


# NODES OF THE NETWORK 


class SenderNode(Node):
    """Sender node in the Direct Conversion Protocol.

    A sender has three components: 1) transmon; 2) detector; 3) transducer

    Attributes:
        name (str):          name of the node
        timeline (Timeline): timeline
        transmon_name (str): name of the transmon
        detector_name (str): name of the detector
        counter2 (Counter):  the counter for the detector
        transducer_name (str): name of the transducer
        counter (Counter):   the counter for the transducer
        emitting_protocol (EmittingProtocol): the protocol for emitting photons
        upconversion_protocol (UpConversionProtocol): the protocol for up converting the microwave to optical photon
    """
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)

        # transmon
        self.transmon_name = name + ".transmon"
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline,
                            wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH],
                            photon_counter=0, efficiency=TRANSMON_EFFICIENCY, photons_quantum_state=state_list)
        self.add_component(transmon)

        # detector
        detector_name = name + ".fockdetector"
        detector = FockDetector(detector_name, timeline, wavelength=MICROWAVE_WAVELENGTH,
                                efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
        self.add_component(detector)
        self.counter2 = Counter()
        detector.attach(self.counter2)

        # transducer
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        self.counter = Counter()
        transducer.attach(self.counter)

        # add receivers
        transmon.add_receiver(transducer)
        transducer.add_outputs([node2, detector])

        # emitting protocol and upconversion protocol
        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol",
                                                  timeline, transmon, transducer)
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol",
                                                          timeline, transducer, node2, transmon)


class ReceiverNode(Node):
    """Receiver node in the Direct Conversion Protocol. 
    
    A receiver has three components: 1) transmon; 2) fock detector; 3) transducer

    Attributes:
        name (str):               name of the node
        timeline (Timeline):      the timeline
        transmon_name (Transmon): name of the transmon
        detector_name (str):      name of the fock detector
        counter2 (Counter):       counter for the fock detector
        transducer_name (str):    name of the transducer
        counter (Counter):        counter for the transducer
        downconversion_protocol (DownConversionProtocol): convert photon into microwave
    """
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        self.transmon_name = name + ".transmon"
        self.detector_name = name + ".fockdetector"
        self.counter2 = Counter()
        self.transducer_name = name + ".transducer"
        self.counter = Counter()

        # transmon
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline,
                            wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH],
                            photons_quantum_state=state_list, photon_counter=0, efficiency=1)
        self.add_component(transmon)
        
        # fock detector
        detector = FockDetector(self.detector_name, timeline, wavelength=OPTICAL_WAVELENGTH,
                                efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector)
        detector.attach(self.counter2)

        # transducer
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_DOWN)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)
        transducer.add_outputs([transmon, detector])

        # down conversion protocol
        self.downconversion_protocol = DownConversionProtocol(self, name + ".downconversion_protocol",
                                                              timeline, transducer, transmon)

    def receive_photon(self, src, photon):
        self.components[self.transducer_name].receive_photon_from_channel(photon)


# MAIN

if __name__ == "__main__":

    runtime = 10e12
    tl = Timeline(runtime)
   
    node2 = ReceiverNode("node2", tl)
    node1 = SenderNode("node1", tl, node2)

    # NOTE: this quantum channel is not used
    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)

    if 0 <= EFFICIENCY_UP <= 1 and 0 <= EFFICIENCY_DOWN <= 1:
        pass
    else:
        raise ValueError("Error: the efficiency must be between 0 and 1")

    # Plot1
    failed_up_conversions = []
    failed_down_conversions = []
    successful_conversions = [] 

    # Plot2
    ideal_photons = []
    emitted_photons = []  
    converted_photons = []
    
    total_photons_successful = 0
    total_transducer_count = 0
    cumulative_time = START_TIME
    
    # Node1
    transmon1   = node1.get_components_by_type("Transmon")[0]
    transducer1 = node1.get_components_by_type("Transducer")[0]
    detector1   = node1.get_components_by_type("FockDetector")[0]

    # Node2
    transmon2   = node2.get_components_by_type("Transmon")[0]
    transducer2 = node2.get_components_by_type("Transducer")[0]
    detector2   = node2.get_components_by_type("FockDetector")[0]

    print(f"--------------------")
    print(f"Direct Quantum Transduction Protocol starts, the qubit that we are going to convert is: {KET1}")
    
    for trial in range(NUM_TRIALS): 

        print(f"--------------------")
        print(f"Trial {trial}:")
        
        # reset timeline   # NOTE should not reset timeline, instead, each experiment should keep running for some time.
        tl.time = 0
        tl.init()

        # Reset counters
        transmon1.photon_counter   = 0 
        transducer1.photon_counter = 0
        detector1.photon_counter   = 0
        transmon2.photon_counter   = 0 
        transducer2.photon_counter = 0
        detector2.photon_counter   = 0

        # NOTE: there should only be one event to kick the simulation (following 2 events shouldn't exist here)
        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time + EMISSION_DURATION) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)

        # NOTE: class Photon shouldn't be the parameter, it should be Photon object
        process1 = Process(node1.upconversion_protocol, "start", [Photon])
        event_time1 = (event_time0 + CONVERSION_DURATION) 
        event1 = Event(event_time1, process1)
        tl.schedule(event1)

        # NOTE: class Photon shouldn't be the parameter, it should be Photon object
        process2 = Process(node2.downconversion_protocol, "start", [Photon])
        event_time2 =(event_time1 + CONVERSION_DURATION) 
        event2 = Event(event_time2, process2)
        tl.schedule(event2)
        
        # run the simulation
        tl.run()

        # get the simulation results
        failed_up_conversions.append(detector1.photon_counter)
        failed_down_conversions.append(detector2.photon_counter)
        successful_conversions.append(transmon2.photon_counter)
        
        print(f"Number of photons converted at time {tl.time}: {transmon2.photon_counter}") 
        total_photons_successful += transmon2.photon_counter
        total_transducer_count += transducer1.photon_counter
        cumulative_time += PERIOD

        ideal_photons.append(trial + 1)
        emitted_photons.append(total_transducer_count)
        converted_photons.append(total_photons_successful)
        

    # RESULTS

    print(f"- - - - - - - - - -")
    print(f"Period: {PERIOD}")

    total_photons_to_be_converted = NUM_TRIALS-1
    print(f"Total number of photons converted: {total_photons_successful}")
    print(f"Total number of photons EMITTED: {total_transducer_count}")

    if total_photons_to_be_converted > 0:
        conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100
    else:
        conversion_percentage = 0
    print(f"Conversion efficiency of DQT protocol with non-idealities of transmon: {conversion_percentage:.2f}%")

    if total_photons_to_be_converted > 0:
        conversion_percentage_2 = (total_photons_successful / total_transducer_count) * 100
    else:
        conversion_percentage_2 = 0
    print(f"Conversion efficiency of DQT protocol: {conversion_percentage_2:.2f}%")

    failed_down_conversions_adjusted = [x + 1 for x in failed_down_conversions]
    successful_conversions_adjusted = [y + 2 for y in successful_conversions]

    print(f"- - - - - - - - - -")

    time_points = [i * PERIOD for i in range(NUM_TRIALS)]


results_matrix = np.zeros((NUM_TRIALS, 3))
for i in range(NUM_TRIALS):
    if failed_up_conversions[i] != 0:
        results_matrix[i, 0] = 1  
    if failed_down_conversions[i] != 0:
        results_matrix[i, 1] = 1  
    if successful_conversions[i] != 0:
        results_matrix[i, 2] = 1  

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [4, 1]})

ax1.plot(time_points, ideal_photons, 'o-', label="Ideal Successfully Converted Photons", color='darkblue')
ax1.plot(time_points, converted_photons, 'o-', label="Successfully Converted Photons", color='#FF00FF')
ax1.set_ylabel("Photon Number", fontsize=24)
ax1.set_title("Photon Conversion over Time", fontsize=24, fontweight='bold')
ax1.legend(fontsize=24, loc='upper left')
ax1.grid(True)
ax1.tick_params(axis='both', labelsize=18)

ax2.bar(time_points, results_matrix[:, 0], color='#ED213C', label='Failed Up', alpha=0.7, width=PERIOD * 0.8)
ax2.bar(time_points, results_matrix[:, 1], color='blue', label='Failed Down', alpha=0.7, bottom=results_matrix[:, 0], width=PERIOD * 0.8)
ax2.bar(time_points, results_matrix[:, 2], color='#119B70', label='Successful', alpha=0.7, bottom=results_matrix[:, 0] + results_matrix[:, 1], width=PERIOD * 0.8)
ax2.set_xlabel(r"Time ($\mu$s)", fontsize=24)
ax2.legend(fontsize=18, loc='upper left')
ax2.tick_params(axis='both', labelsize=12)
ax2.yaxis.set_visible(False)  
ax2.legend(fontsize=12, loc='upper left')
ax2.tick_params(axis='both', labelsize=12)

plt.tight_layout()
plt.show()
