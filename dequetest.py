from collections import deque


class dq:
    def __init__(self):
        self.d = deque(maxlen=10)
    def append(self, x):
        self.d.append(x)
    def appendleft(self, x):
        self.d.appendleft(x)
    def pop(self):
        return self.d.pop()
    def popleft(self):
        return self.d.popleft()
    def __str__(self):
        return str(self.d)
    def __len__(self):
        return len(self.d)
    def __getitem__(self, i):
        return self.d[i]
    def __setitem__(self, i, x):
        self.d[i] = x
    def __delitem__(self, i):
        del self.d[i]
    def __iter__(self):
        return iter(self.d)
    def __reversed__(self):
        return reversed(self.d)
    def clear(self):
        self.d.clear()
    def count(self, x):
        return self.d.count(x)
    def extend(self, x):
        self.d.extend(x)
    def extendleft(self, x):
        self.d.extendleft(x)
    def index(self, x):
        return self.d.index(x)
    def insert(self, i, x):
        self.d.insert(i, x)
    def remove(self, x):
        self.d.remove(x)
    def reverse(self):
        self.d.reverse()
    def rotate(self, n):
        self.d.rotate(n)
d = dq()
d.append("A")
print(d)
d.append("B")
print(d)
d.append("C")
print(d)
d.append("D")
print(d)
d.append("E")
print(d)
d.append("F")  
print(d)
d.append("G")
print(d)
d.append("H")
print(d)
d.append("I")
print(d)
d.append("J")
print(d)
d.append("K")
print(d)

print(list(d))
