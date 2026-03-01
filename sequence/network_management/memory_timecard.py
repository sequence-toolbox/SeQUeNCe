from .reservation import Reservation


class MemoryTimeCard:
    """Class for tracking reservations on a specific memory.
       Each quantum memory in a memory array is associated with a memory time card

    Attributes:
        memory_index (int): index of memory being tracked (in the memory array).
        reservations (list[Reservation]): list of reservations for the memory.
    """

    def __init__(self, memory_index: int):
        """Constructor for time card class.

        Args:
            memory_index (int): index of memory to track.
        """

        self.memory_index = memory_index
        self.reservations = []

    def add(self, reservation: Reservation) -> bool:
        """Method to add reservation.

        Will use the schedule_reservation() to determine the index to insert reservation.

        Args:
            reservation (Reservation): reservation to add.

        Returns:
            bool: whether reservation was inserted successfully.
        """

        position = self.schedule_reservation(reservation)
        if position >= 0:
            self.reservations.insert(position, reservation)
            return True
        else:
            return False

    def remove(self, reservation: Reservation) -> bool:
        """Method to remove a reservation.

        Args:
            reservation (Reservation): reservation to remove.

        Returns:
            bool: if a reservation was already on the memory (return True) or not (return False).
        """

        try:
            position = self.reservations.index(reservation)
            self.reservations.pop(position)
            return True
        except ValueError:
            return False

    def schedule_reservation(self, reservation: Reservation) -> int:
        """Method to add reservation to a memory.

        Will return the index at which reservation can be inserted into memory reservation list.
        If no space is found for reservation, will raise an exception.

        Args:
            reservation (Reservation): reservation to schedule.

        Returns:
            int: index to insert a reservation in the reservation list.

        Raises:
            Exception: no valid index to insert reservation.
        """

        start, end = 0, len(self.reservations) - 1
        while start <= end:
            mid = (start + end) // 2
            if self.reservations[mid].start_time > reservation.end_time:
                end = mid - 1
            elif self.reservations[mid].end_time < reservation.start_time:
                start = mid + 1
            elif (max(self.reservations[mid].start_time, reservation.start_time) <=
                  min(self.reservations[mid].end_time, reservation.end_time)):
                return -1
        return start
