import heapq

class EventList:
    def __init__(self):
        self.__data = []

    def __len__(self):
        return len(self.__data)

    def push(self, event):
        heapq.heappush(self.__data, event)

    def pop(self):
        return heapq.heappop(self.__data)

    def empty(self):
        return len(self.__data) == 0
