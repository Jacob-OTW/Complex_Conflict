class LinkedCircle:
    class Node:
        def __init__(self, data):
            self.previous_node = None
            self.data = data
            self.next_node = None

    def __init__(self, *data):
        self.head = None
        self.cur = self.head

        for data_sin in data:
            self.add(data_sin)

    def last_node(self):
        return self.head.previous_node

    def add(self, data):
        node = self.Node(data)
        if self.head is None:
            self.head = node
            self.head.next_node = self.head
            self.head.previous_node = self.head
            self.cur = self.head
        else:
            last_node = self.last_node()
            node.previous_node = last_node
            node.next_node = self.head
            last_node.next_node = node
            self.head.previous_node = node

    def next(self):
        self.cur = self.cur.next_node

    def previous(self):
        self.cur = self.cur.previous_node
