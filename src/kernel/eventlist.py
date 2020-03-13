import heapq

class EventList:
    def __init__(self):
        self.data = []

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        for data in self.data:
            yield data

    def push(self, event):
        heapq.heappush(self.data, event)

    def pop(self):
        return heapq.heappop(self.data)

    def isempty(self):
        return len(self.data) == 0
