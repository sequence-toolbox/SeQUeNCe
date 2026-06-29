"""Quantum transduction via direct conversion
"""

import sys
sys.path.append('.')

import numpy as np
import matplotlib.pyplot as plt

from fock_quantum_channel import FockQuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.transmon import Transmon, EmittingProtocol
from sequence.components.transducer import Transducer, UpConversionProtocol, DownConversionProtocol
from sequence.components.detector import FockDetector
from sequence.constants import KET0, KET1
from sequence.components.transmon import EmittingProtocol


# GENERAL

NUM_TRIALS = 100
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm

# Timeline
START_TIME = 0
PERIOD = 1 # mus

state_list= [KET1, KET0] 

TRANSMON_EFFICIENCY = 1

# Transducer
EFFICIENCY_UP   = 0.5
EFFICIENCY_DOWN = 0.5

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0.95 #typical attenuation for a optical fiber at 1550 nm
DISTANCE = 1e3 #1km


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
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        # transmon
        self.transmon_name = name + ".transmon"
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline, wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], \
                            photon_counter=0, efficiency=TRANSMON_EFFICIENCY, photons_quantum_state=state_list)
        self.add_component(transmon)

        # detector
        detector_name = name + ".fockdetector"
        detector = FockDetector(detector_name, timeline, wavelength=MICROWAVE_WAVELENGTH, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
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

        # emitting protocol and upconversion protocol
        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, transmon, transducer)
        transducer.up_conversion_protocol = UpConversionProtocol(self, name + "up_conversion_protocol", timeline, transducer)

       
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
        self.first_component_name=self.transducer_name

        # transmon
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline, wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], \
                            photons_quantum_state=state_list, photon_counter=0, efficiency=1)
        self.add_component(transmon)
        
        # fock detector
        detector = FockDetector(self.detector_name, timeline, wavelength=OPTICAL_WAVELENGTH, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector)
        detector.attach(self.counter2)

        # transducer
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_DOWN)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.attach(self.counter)

        #first component name and outputs
        self.set_first_component(self.transducer_name)
        transducer.add_outputs([transmon, detector])

        transducer.down_conversion_protocol = DownConversionProtocol(self, name + "down_conversion_protocol", timeline, transducer)



# MAIN

if __name__ == "__main__":

    runtime = 10e12
    tl = Timeline(runtime)
   
    node1 = SenderNode("node1", tl)
    node2 = ReceiverNode("node2", tl)

    qc1 = FockQuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)    
    qc1.set_ends(node1, node2)

    if EFFICIENCY_UP >= 0 and EFFICIENCY_UP <= 1 and EFFICIENCY_DOWN >= 0 and EFFICIENCY_DOWN <= 1:
        pass
    else:
        print("Error: the efficiency must be between 0 and 1")
        exit(1)

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
    transmon1.add_receiver(transducer1)
    transducer1.add_outputs([qc1, detector1])

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

        detector1.photon_counter   = 0
        transmon2.photon_counter   = 0 
        detector2.photon_counter   = 0

        process0 = Process(node1.emitting_protocol, "start", [])  # NOTE: there should only be one event to kick the simulation (following 2 events shouldn't exist here)
        event_time0 = (cumulative_time) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)
        
        tl.run()

        # get the simulation results
        failed_up_conversions.append(detector1.photon_counter)
        failed_down_conversions.append(detector2.photon_counter)
        successful_conversions.append(transmon2.photon_counter)
        
        print(f"Number of photons converted at time {tl.time}: {transmon2.photon_counter}") 
        total_photons_successful += transmon2.photon_counter

        total_transducer_count += transducer1.photon_counter
        cumulative_time += PERIOD

        ideal_photons.append(trial+1)
        emitted_photons.append(total_transducer_count)
        converted_photons.append(total_photons_successful)

    # RESULTS

    print(f"- - - - - - - - - -")
    print(f"Period: {PERIOD}")

    total_photons_to_be_converted = NUM_TRIALS
    print(f"Total number of photons converted: {total_photons_successful}")

    conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol with no-idealities of transmon: {conversion_percentage:.2f}%")

    failed_down_conversions_adjusted = [x + 1 for x in failed_down_conversions]
    successful_conversions_adjusted = [y + 2 for y in successful_conversions]

    print(f"- - - - - - - - - -")

    time_points = [i * PERIOD for i in range(NUM_TRIALS)]



#Plot

plt.figure(figsize=(10, 6))

# Plot the conversion results with distinct styles for clarity
plt.plot(time_points, failed_up_conversions, color='blue', label='Failed Up Conversions', linewidth=2)
plt.plot(time_points, failed_down_conversions, color='red', label='Failed Down Conversions', linewidth=2)
plt.plot(time_points, successful_conversions, color='green', label='Successful Conversions', linewidth=2)

plt.xlabel(r"Time ($\mu$s)", fontsize=14)
plt.ylabel('Number of Conversions', fontsize=14)
plt.title('Quantum Transduction Results', fontsize=16)
plt.legend()

plt.grid(True)
plt.show()


results_matrix = np.zeros((NUM_TRIALS, 3))
for i in range(NUM_TRIALS):
    if failed_up_conversions[i] != 0:
        results_matrix[i, 0] = 1  
    if failed_down_conversions[i] != 0:
        results_matrix[i, 1] = 1  
    if successful_conversions[i] != 0:
        results_matrix[i, 2] = 1  

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [4, 1]})

l1, = ax1.plot(time_points, ideal_photons, 'o-', label="Ideal Successfully Converted Photons", color='darkblue', markersize=3)
l2, = ax1.plot(time_points, converted_photons, 'o-', label="Successfully Converted Photons", color='#FF00FF', markersize=3)
ax1.set_ylabel("Photon Number", fontsize=34)
ax1.set_title("Photon Conversions over Time", fontsize=34, fontweight='bold')

ax1.tick_params(axis='both', labelsize=30)

b1 = ax2.bar(time_points, results_matrix[:, 0], color='#ED213C', label='Failed Up-conversion', alpha=0.8, width=PERIOD* 0.8, align='edge')
b2 = ax2.bar(time_points, results_matrix[:, 1], color='blue', label='Failed Down-conversion', alpha=0.8, bottom=results_matrix[:, 0], width=PERIOD * 0.8, align='edge')
b3 = ax2.bar(time_points, results_matrix[:, 2], color='#119B70', label='Successful conversions', alpha=0.8, bottom=results_matrix[:, 0] + results_matrix[:, 1], width=PERIOD * 0.8, align='edge')
ax2.set_xlabel(r"Time ($\mu$s)", fontsize=34)
ax2.yaxis.set_visible(False)  
ax2.grid(True)
ax2.tick_params(axis='both', labelsize=30)

ax1.legend(
    handles=[l1, l2, b1, b2, b3],
    labels=[
        "Ideal Successfully Converted Photons",
        "Successfully Converted Photons",
        "Failed Up-conversion",
        "Failed Down-conversion",
        "Successful conversions"
    ],
    loc='upper left',     
    fontsize=20,
    frameon=True,
    shadow=False
)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()