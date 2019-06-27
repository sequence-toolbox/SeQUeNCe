import heapq

class EventList:
    def __init__(self):
        self.__data = []

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        for data in self.__data:
            yield data

    def push(self, event):
        heapq.heappush(self.__data, event)

    def pop(self):
        return heapq.heappop(self.__data)

    def isempty(self):
        return len(self.__data) == 0
