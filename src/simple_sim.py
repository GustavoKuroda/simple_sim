"""
A Python functional extension for discrete event simulation based in 'SMPL' (original C version by Myron H. MacDougall)
"""

# Copyright (c) 2022 Gustavo Kenji Kuroda de Oliveira
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import heapq
import math
import sys
from collections import deque

RESERVED = 0
QUEUED = 1

class Event:
    """
    Information about the events of the simulation.
    """
    def __init__(self, kind, time, costumer):
        # kind of event - '1' = arrival, '2' = request, '3' = release
        self.kind = kind

        # time of occurrence
        self.time = time

        # client associated
        self.costumer = costumer

    def __lt__(self, other):
        """
        Compare the time of occurrence of two events.
        - Parameters:
            - other (Event): event to be compared to.
        - Returns:
            - True, if self.time is lower than other.time
            - False, if self.time is greater than other.time
        """
        return self.time < other.time

class FEL:
    """
    Implementation of future events list as a queue (class heapq).
    """
    def __init__(self):
        # future events list
        self._queue = []

    def append(self, e):
        """
        Add a new event to the queue.
        - Parameters:
            - e (Event): new event to be added.
        """
        heapq.heappush(self._queue, e)


    def trigger(self):
        """
        Trigger the head queue event.
        - Returns:
            - The event to be executed.
        """
        e = heapq.heappop(self._queue)
        return e

class ResourceData:
    """
    Data of the resources.
    """
    def __init__(self, total_servers):
        """
        Object to store the resources data.
        - Parameters:
            - total_servers (int): Number of servers (resources).
        """
        self.total_servers = total_servers
        self.busy_servers = 0
        self.servers = [None] * total_servers
        for i in range(0, total_servers):
            self.servers[i] = Resource(i)

class Resource:
    """
    A instance of a resource.
    """
    def __init__(self, index):
        """
        Create a resource.
        - Parameters:
            - index (int): Identifier of the resource
        """
        self.index = index
        self.costumer = 0
        self.busy = False
        self.busy_time = 0.0
        self.total_busy_time = 0.0

class Model:
    """
    A discrete event simulation model.
    """
    def __init__(self, total_sim_time, inter_arrival_time, service_time, sequence):
        """
        Initialize the center of service (model).
        - Parameters:
            - total_sim_time (float): Total time of the simulation.
            - inter_arrival_time (float): Mean time between costumers to arrive.
            - service_time (float): Mean time to completion.
            - resources (int): Number of servers.
        """
        # time of simulation
        self.now = 0.0

        # total simulation time
        self.total_sim_time = total_sim_time

        # FEL
        self.fel = FEL()

        # request queue
        self.req_queue = deque()

        # mean inter arrival time of clients
        self.inter_arrival_time = inter_arrival_time

        # mean service time
        self.service_time = service_time

        # number of available resources
        self._resources = {}

        # counter of costumers
        self.costumer = 1

        # state variable (number of events triggered)
        self.count = 0

        # schedules the first event
        if sequence == 1:
            self.schedule('1', 0.0, self.costumer)

        # pseudo-random number generator.
        self._rand = Rand()

        # trace the events
        self._trace = False

    def init(self, name):
        """
        Name the center of service (model).
        Initializes the metrics variables.
        - Parameters:
            - name (string): The model name.
        """
        if name is None:
            raise ValueError("The model must be named.")

        self._model_name = name

        # output stream
        self._output = sys.stdout

        # metrics variables
        self._queue_exit_counts = 0
        self.release_count = 0
        self._queue_length = 0
        self.total_queueing_time = 0
        self.time_of_last_change = 0

    def time(self):
        """
        Gets the current time in the simulated environment.
        This value does not change until cause() is invoked.
        - Returns:
            - The current time in the simulated environment.
        """
        return self.now

    def trace(self, trace_enable):
        """
        Turns trace on and off.
        - Parameters:
            - trace_enable (bool): True to track the events.
        """
        self._trace = trace_enable

    def resource(self, total_servers):
        """
        Abstraction of a resource.
        - Parameters:
            - total_servers (int): Number of servers.
        """
        if total_servers <= 0:
            raise ValueError("There must be at least one server.")

        self._resources = ResourceData(total_servers)

    def schedule(self, kind, time_of_occur, costumer):
        """
        Schedules a event based on the time of occurrence.
        - Parameters:
            - kind (char): '1' = arrival, '2' = request, '3' = release.
            - time_of_occur (float): time of occurrence of the event.
            - costumer (int): number of the costumer associated to the event.
        """
        # append a object Event to the fel
        e = Event(kind, self.time() + time_of_occur, costumer)
        self.fel.append(e)

    def request(self, costumer):
        """
        If a resource is free, request() reserves the resource,
        returning RESERVED. In case there is no resource(s), request() 
        enqueue the request and return QUEUED.
        - Parameters:
            - costumer (int): costumer related to the request.
        - Returns:
            - RESERVED, if there is a free resource.
            - QUEUED, if there is no free resource(s).
        """
        if self._resources.busy_servers < self._resources.total_servers:
            chosen = None
            for iterator in range (0, self._resources.total_servers):
                server = self._resources.servers[iterator]
                if server.busy is False:
                    chosen = server
                    break

            chosen.busy = True
            chosen.busy_time = self.now
            chosen.costumer = costumer

            self._resources.busy_servers += 1

            if self._trace:
                print("({}) \tCostumer {} requested and accessed at {}.".format(self._model_name, costumer, self.time()))
            return RESERVED
        else:
            # calculate the total queueing time
            self.total_queueing_time += self._queue_length * (self.now - self.time_of_last_change)
            self._queue_length += 1
            self.time_of_last_change = self.now

            # enqueue the request
            self.req_queue.append(costumer)
            
            if self._trace:
                print("({}) \tCostumer {} requested but queued at {}. (inq = {})".format(self._model_name, costumer, self.time(), len(self.req_queue)))
            return QUEUED

    def release(self, costumer):
        """
        If a request was enqueued, release() dequeue the request,
        putting it at the head of the FEL.
        """
        # release count
        self.release_count += 1
        
        matching_server = None
        for iterator in range(0, self._resources.total_servers):
            server = self._resources.servers[iterator]
            if server.costumer == costumer:
                matching_server = server
                break

        if matching_server is None:
            raise ValueError("There is no server reserved for the given costumer.")
            
        matching_server.busy = False
        matching_server.total_busy_time += self.now - matching_server.busy_time

        self._resources.busy_servers -= 1

        if self._trace:
            print("({}) \tCostumer {} leaving at {}.".format(self._model_name, self.costumer, self.time()))

        if len(self.req_queue) > 0:
            # dequeue an enqueued request
            costumer = self.req_queue.popleft()
            self.schedule('3', self._rand.expntl(self.service_time) , costumer)

            # calculate the total queueing time
            self.total_queueing_time += self._queue_length * (self.now - self.time_of_last_change)
            self._queue_length -= 1
            self.time_of_last_change = self.now

            # increase queue exits
            self._queue_exit_counts += 1

            matching_server.busy = True
            matching_server.busy_time = self.now
            matching_server.costumer = costumer

            self._resources.busy_servers += 1

            if self._trace:
                print("({}) \tCostumer {} dequeued and accessed at {}. (inq = {})".format(self._model_name, costumer, self.time(), len(self.req_queue)))

    def cause(self):
        """
        Dequeue the head of FEL, increase the time of simulation
        to the time of occurrence of the dequeued event.
        - Returns:
            - Head event of FEL.
        """
        # trigger a event, set the time of simulation and current costumer
        e = self.fel.trigger()
        self.now = e.time
        self.costumer = e.costumer

        if e.kind == '1' and self._trace:
            print("({}) \tCostumer {} arrived at {}.".format(self._model_name, self.costumer, self.time()))
        return e

    def U(self):
        """
        Calculate the utilization of the resource.
        Sum the percentage use of each server when it was busy.
        - Returns:
            - The utilization of the servers
        """
        utilization = 0.0
        for iterator in range(0, self._resources.total_servers):
            server = self._resources.servers[iterator]
            utilization += server.total_busy_time
        utilization /= self.total_sim_time
        return utilization

    def B(self):
        """
        Calculate the mean busy time of a resource.
        The busy time of a server is the time spent to a completion
        of a request.
        - Returns:
            - The mean busy time of a resource.
        """
        total_busy_time = 0.0
        for iterator in range(0, self._resources.total_servers):
            server = self._resources.servers[iterator]
            total_busy_time += server.total_busy_time
        return (total_busy_time / self.release_count) if self.release_count > 0 else total_busy_time

    def report(self):
        """
        Generates a report message with utilization, mean
        busy time, average queue length, total releases 
        and queue exits count.
        """
        self._output.write("\n")
        self._output.write("\t-----------SIMULATION REPORT-----------\t\n")
        self._output.write("Model name: %-17s\n" % self._model_name)
        self._output.write("Time: %.2f\n" % self.time())
        self._output.write("Resource (servers): %d\n" % self._resources.total_servers)
        self._output.write("Utilization: %.2f\n" % self.U())
        self._output.write("Mean busy time: %.2f\n" % self.B())
        self._output.write("Average queue length: %.2f\n" % (self.total_queueing_time / self.total_sim_time))
        self._output.write("Total releases: %d\n" % self.release_count)
        self._output.write("Queue exits: %d\n" % self._queue_exit_counts)

class Rand:
    """
    A Python implementation of the pseudo-random number generator of 'smpl'.
    """

    DEFAULT_STREAMS = [ 1973272912, 747177549, 20464843, 640830765, 1098742207, 78126602, 84743774, 831312807, 124667236, 1172177002, 1124933064, 1223960546, 1878892440, 1449793615, 553303732 ]
    """
    Default seeds for streams 1-15.
    """

    A = 16807
    """
    Multiplier (7**5) for 'ranf'.
    """

    M = 2147483647
    """
    Modulus (2**31-1) for 'ranf'.
    """

    def __init__(self):
        # Seed for current stream.
        self._seed = 0

    def stream(self, stream_number):
        """
        Change the current generator stream.
        Valid stream numbers range from 1 to 15.
        - Parameters:
            - stream_number (int): The generator stream number.
        """

        if (stream_number < 1) or (stream_number > 15):
            raise ValueError("Illegal random number generator stream!")

        self._seed = Rand.DEFAULT_STREAMS[stream_number - 1]

    def ranf(self):
        """
        Generates a pseudo-random value from an uniform distribution ranging
        from 0 to 1.
        - Returns:
            - The generated pseudo-random number.
        """

        # The comments below are based on the original comments of 'smpl'.
        # In the comments, The lower short of I is called 'L', an the higher short of I is called 'H'.

        # 16807*H->Hi
        # [C] p=(short *)&I
        # [C] Hi=*(p+1)*A
        # (p is pointer to I)
        hi = get_short1(self._seed) * Rand.A

        # 16807*L->Lo
        # [C] *(p+1)=0
        # (p is pointer to I)
        self._seed = set_short1(self._seed, 0)

        # [C] Lo=I*A
        # (p is pointer to I)
        lo = self._seed * Rand.A

        # add high-order bits of Lo to Hi
        # [C] p=(short *)&Lo
        # [C] Hi+=*(p+1)
        # (p is pointer to Lo)
        hi += get_short1(lo)

        # low-order bits of Hi->LO
        # [C] q=(short *)&Hi
        # (q is pointer to Hi)

        # clear sign bit
        # [C] *(p+1)=*q&0X7FFF
        # (p is pointer to Lo, q is pointer to Hi)
        lo = set_short1(lo, get_short0(hi) & 0x7FFF)

        # Hi bits 31-45->K
        # [C] k=*(q+1)<<1
        # [C] if (*q&0x8000) { k++ }
        # (q is pointer to Hi)
        k = get_short1(hi) << 1
        if (get_short0(hi) & 0x8000) != 0:
            k += 1

        # form Z + K [- M] (where Z=Lo): presubtract M to avoid overflow
        lo -= Rand.M
        lo += k
        if lo < 0:
            lo += Rand.M
        self._seed = lo

        # Lo x 1/(2**31-1)
        return (lo * 4.656612875E-10)

    def expntl(self, mean):
        """
        Generates a pseudo-random value from an exponential distribution.
        - Parameters:
            - mean (double): The mean value.
        - Returns:
            - The generated pseudo-random number.
        """
        return -mean * math.log(self.ranf())

def set_short0(int_value, short_value):
    """
    Sets the least significant short of an integer.
    - Parameters:
        - int_value (int): The integer.
        - short_value (int): The short.
    - Returns:
        - The integer with the least significant short replaced.
    """
    return (int_value & 0xFFFF0000) | (short_value & 0x0000FFFF)

def set_short1(int_value, short_value):
    """
    Sets the most significant short of an integer.
    - Parameters:
        - int_value (int): The integer.
        - short_value (int): The short.
    - Returns:
        - The integer with the most significant short replaced.
    """
    return (int_value & 0x0000FFFF) | ((short_value << 16) & 0xFFFF0000)

def get_short0(int_value):
    """
    Gets the least significant short of an integer.
    - Parameters:
        - int_value (int): The integer.
    - Returns:
        - The least significant short of the integer.
    """
    return int_value & 0x0000FFFF

def get_short1(int_value):
    """
    Gets the most significant short of an integer.
    - Parameters:
        - int_value (int): The integer.
    - Returns:
        - The most significant short of the integer.
    """
    return (int_value >> 16) & 0x0000FFFF