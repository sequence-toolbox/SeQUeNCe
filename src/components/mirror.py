class Mirror(Entity):

      def __init__(self, name: str, timeline: "Timeline", fidelity=0.98, time_resolution=150, frequency=8e7, wavelength=1550, bandwidth=0, mean_photon_num=0.1,
                    encoding_type=polarization, phase_error=0):

            Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
            self.fidelity = fidelity
            self.receivers = []
            # for BB84
            self.start_time = 0
            self.basis_list = []
            self.photon_counter = 0
            self.time_resolution = time_resolution  # measured in ps

            self.frequency = frequency  # measured in Hz
            self.wavelength = wavelength  # measured in nm
            self.linewidth = bandwidth  # st. dev. in photon wavelength (nm)
            self.mean_photon_num = mean_photon_num
            self.encoding_type = encoding_type
            self.phase_error = phase_error

      def init(self):

            pass

      def get(self, dark_get=False) -> None:

            self.photon_counter += 1
            now = self.timeline.now()
            time = round(now / self.time_resolution) * self.time_resolution

      def emit(self, state_list, dst: str) -> None:

            time = self.timeline.now()
            period = int(round(1e12 / self.frequency))

            for i, state in enumerate(state_list):

                num_photons = 1

                if random.random_sample() < self.phase_error:
                    state = multiply([1, -1], state)

                for _ in range(num_photons):
                    wavelength = self.linewidth * random.randn() + self.wavelength
                    new_photon = Photon(str(i),
                                        wavelength=wavelength,
                                        location=self.owner,
                                        encoding_type=self.encoding_type,
                                        quantum_state=state)
                    
                    process = Process(self.owner, "send_qubit", [dst, new_photon])
                    
                    event = Event(time, process)
                    self.owner.timeline.schedule(event)
                    self.photon_counter += 1
                time += period
