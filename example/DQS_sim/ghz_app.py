from sequence.app.request_app import RequestApp


class GHZApp(RequestApp):
    def get_memory(self, info) -> None:
        """Method to receive entangled memories.

        Does nothing for this class.

        Args:
            info (MemoryInfo): info on the qualified entangled memory.
        """

    def remove_memo_reserve_map(self, index: int) -> None:
        pass
