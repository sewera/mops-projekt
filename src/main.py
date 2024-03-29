import argparse
import json
from simulator.rand import Rand
from typing import List

import data_reader
from logger import Logger
from simulator.event_queue import EventQueue
from simulator.packet_generator import PacketGenerator
from simulator.queue import Queue
from simulator.state import SimulationParameters
from simulator.timer import Timer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--length", help="Packet length", type=int, required=True)
    parser.add_argument(
        "-t", "--simulationtime", help="Simulation time", type=float, required=True
    )
    parser.add_argument(
        "-g",
        "--generationconstant",
        help="Generation time = Packet length * Generation constant",
        type=float,
        required=True,
    )
    parser.add_argument(
        "-q",
        "--queueconstant",
        help="Handling time = Packet length * Queue constant",
        type=float,
        required=True,
    )
    parser.add_argument(
        "-o",
        "--lambdaon",
        help="Lambda parameter for ON state",
        type=float,
        required=True,
    )
    parser.add_argument(
        "-f",
        "--lambdaoff",
        help="Lambda parameter for OFF state",
        type=float,
        required=True,
    )
    parser.add_argument(
        "-n", "--streams", help="Number of streams", type=int, required=True
    )
    parser.add_argument(
        "-d",
        "--dropped",
        help="Number of dropped streams after the first queue",
        type=int,
        required=True,
    )
    args = parser.parse_args()

    simulation_params = SimulationParameters(
        args.simulationtime,
        args.length,
        args.generationconstant,
        args.queueconstant,
        args.lambdaon,
        args.lambdaoff,
        args.streams,
        args.dropped,
    )
    Logger.set_logger_params()
    log = Logger(None)

    if simulation_params.streams_number <= simulation_params.dropped_streams:
        log.error(
            "The number of dropped streams has to be lower than "
            "the number of streams going into the first queue"
        )
        exit(1)

    simulation_time = simulation_params.simulation_time
    timer = Timer()
    event_queue = EventQueue(simulation_time, timer)
    queue_two = Queue(
        timer,
        event_queue,
        simulation_params.packet_length,
        simulation_params.queue_constant,
    )
    queue_one = Queue(
        timer,
        event_queue,
        simulation_params.packet_length,
        simulation_params.queue_constant,
        queue_two,
    )

    rand = Rand(simulation_params.lambda_on, simulation_params.lambda_off)

    generator_pool: List[PacketGenerator] = []

    for _ in range(
        simulation_params.streams_number - simulation_params.dropped_streams
    ):
        generator = PacketGenerator(
            timer,
            event_queue,
            queue_one,
            rand,
            simulation_params.packet_length,
            simulation_params.generation_constant,
            True,
        )
        generator_pool.append(generator)

    for _ in range(simulation_params.dropped_streams):
        generator = PacketGenerator(
            timer,
            event_queue,
            queue_one,
            rand,
            simulation_params.packet_length,
            simulation_params.generation_constant,
            False,
        )
        generator_pool.append(generator)

        generator = PacketGenerator(
            timer,
            event_queue,
            queue_two,
            rand,
            simulation_params.packet_length,
            simulation_params.generation_constant,
            True,
        )
        generator_pool.append(generator)

    while event_queue.handle_event():
        log.debug(f"Time: @{timer.current_time:.2f}")

    log.debug("queue one data:")
    log.debug(f"{str(queue_one.packets_number)[:100]} --clip--")
    log.debug(f"{str(queue_one.packets)[:100]} --clip--")
    log.debug(f"{str(queue_one.packets_passed)[:100]} --clip--")

    results = {}
    results["avg_queue_length_Q1"] = data_reader.show_queue_length_average(
        queue_one.packets_number
    )
    results[
        "avg_queue_waiting_time_Q1"
    ] = data_reader.show_average_queue_waiting_time_Q1(queue_one.packets_passed)
    results["avg_delay_Q1"] = data_reader.show_average_delay_Q1(
        queue_one.packets_passed
    )
    results["avg_load_Q1"] = data_reader.show_average_server_load_Q1(
        queue_one.packets_passed
    )
    results["packets_passed_Q1"] = len(queue_one.packets_passed)

    log.debug("queue two data:")
    log.debug(f"{str(queue_two.packets_number)[:100]} --clip--")
    log.debug(f"{str(queue_two.packets)[:100]} --clip--")
    log.debug(f"{str(queue_two.packets_passed)[:100]} --clip--")
    results["avg_queue_length_Q2"] = data_reader.show_queue_length_average(
        queue_two.packets_number
    )
    results[
        "avg_queue_waiting_time_Q2"
    ] = data_reader.show_average_queue_waiting_time_Q2(queue_two.packets_passed)
    results["avg_delay_Q2"] = data_reader.show_average_delay_Q2(
        queue_two.packets_passed
    )
    results["avg_load_Q2"] = data_reader.show_average_server_load_Q2(
        queue_two.packets_passed
    )
    results["packets_passed_Q2"] = len(queue_two.packets_passed)
    results["simulation_params"] = {
        "simulation_time": simulation_params.simulation_time,
        "packet_length": simulation_params.packet_length,
        "generation_constant": simulation_params.generation_constant,
        "queue_constant": simulation_params.queue_constant,
        "lambda_on": simulation_params.lambda_on,
        "lambda_off": simulation_params.lambda_off,
        "streams_number": simulation_params.streams_number,
        "dropped_streams": simulation_params.dropped_streams,
    }
    print(json.dumps(results))


if __name__ == "__main__":
    main()
