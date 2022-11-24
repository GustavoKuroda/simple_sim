from simple_sim import Model, RESERVED

# initializes the center of service
model = Model(120, 5.0, 6.0, 1) # total_sim_time, inter_arrival_time, service_time, sequence
model.init('Example M/M/1')
model.resource(1) # total_servers

# to enable trace events, use True
model.trace(True)

# select the pseudo-random generator stream number
model._rand.stream(1)

# execute the simulation
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
