from timeline import Timeline
from entity import Entity
from process import Process
from event import Event
from topology import BSM, Detector, Photon
import encoding
from numpy import random

random.seed(1)
tl = Timeline()
d0 = Detector(tl,efficiency=0.2)
d1 = Detector(tl,efficiency=0.2)
bsm = BSM('bsm',tl,detectors=[d0,d1])
counter = 0

for i in range(500):
    tl.time = 1+i*1e7
    target = Photon('', tl, encoding_type = encoding.time_bin, quantum_state=[complex(0.6), complex(0.8)])
    signal = Photon('', tl, encoding_type = encoding.time_bin)
    idle = Photon('', tl, encoding_type = encoding.time_bin)
    signal.entangle(idle)
    bsm.get(target, 0)
    bsm.get(signal, 1)
    if len(idle.quantum_state) == 2:
        counter+=1
        print(i,idle.quantum_state)

tl.time = 0
tl.init()
tl.run()
res = bsm.get_bsm_res()
print(res)
print(len(res))
print(counter)
