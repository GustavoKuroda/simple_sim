# Overview
 A Python functional extension for discrete event simulation based in 'SMPL' (original C version by Myron H. MacDougall).

# Usage
 To create a simulation using the simple_sim library is necessary to import the following symbols: `Model`, `RESERVED`, and, if necessary, `QUEUED`. Use the command:

 ```
 from simple_sim import Model, RESERVED, QUEUED
 ```

 To create a simulation is necessary to instantiate a `Model` object with some parameters: `total_sim_time`, `inter_arrival_time`, `service_time`,  and `sequence`.

 ```
 model = Model(total_sim_time, inter_arrival_time, service_time, sequence)
 ```

 To initiate the model can be used the `init` method alongside the argument that names the model. `init` names the model and initiates statistics attributes.

 ```
 model.init('Simulation model name')
 ```

 It's also necessary to indicate the number of resources (servers) using the `resource` method.

 ```
 model.resource(1) # total_servers
 ```

 To trace the events and the respective time of occurrence, the `trace` method can be used with the argument `True`.

 ```
 model.trace(True)
 ```

 As the simulation is based on the generation of pseudo-random numbers, it's necessary to indicate one of the fifteen generator streams.

 ```
 model._rand.stream(1) # Valid stream numbers range from 1 to 15.
 ```

 The following code simulates an M/M/1 queue and generates a report message at the end of the simulation.

 ```
 while model.time() <= model.total_sim_time and model.fel._queue:
    e = model.cause()
    model.count += 1
    match e.kind:
        case '1': # arrival
            model.schedule('2', 0.0, model.costumer)
            model.schedule('1', model._rand.expntl(model.inter_arrival_time), model.costumer + 1)

        case '2': # request
            if model.request(model.costumer) is RESERVED:
                model.schedule('3', model._rand.expntl(model.service_time), model.costumer)

        case '3': # completion
            model.release(model.costumer)

 # report of simulation
 model.report()
 ```

 The `cause` method is the simulation heart as it's constantly invoked, by dequeuing an event and increasing the time of simulation to the time of occurrence of this event.

 A simple discrete event simulation has three types of events:
 - 1 - arrival: the arrival of a client at the center of service;
 - 2 - request: the client requests access to the server or service;
 - 3 - release: completion of a client attendance, leaving the server.

 At the initialization of the model, the first arrival is scheduled for immediate execution. Each arrival schedules a request for immediate execution and the subsequent arrival, using `expntl` method from _rand, a `Rand` class object.

 A request is attended if there is a free resource (server), scheduling a release event using `expntl` method. If there isn't a free resource (server), the request is enqueued to future execution.

 Finishing the simulation, the `report` method is invoked to generate a report message with utilization, mean busy time, average queue length, total releases, and queue exits count.
