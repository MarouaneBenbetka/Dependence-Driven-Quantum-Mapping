
import json
import islpy as isl
from src.isl_routing.utils.isl_to_python import *
import os
import ast
from time import time


def json_file_to_isl(file_path: str):
    with open(file_path) as f:
        data = json.load(f)

    read = isl.UnionMap(data["Read"])
    write = isl.UnionMap(data["Write"])
    schedule = isl.UnionMap(data["RecoveredSchedule"])

    access_read = read2access(read, schedule)
    access_write = read2access(write, schedule)
    qasm_code = data["qasm_code"]

    result = {
        "qasm_code": qasm_code,
        "read": access_read,
        "write": access_write,
    }

    return result


def load_qasm(file_path: str):
    with open(file_path) as f:
        data = json.load(f)

    qasm_code = data["qasm_code"]

    result = {
        "qasm_code": qasm_code,
    }

    return result


def extract_multi_qubit_gates(access_map):
    return access_map.subtract(access_map.lexmin().intersect(access_map.lexmax())).domain()


def access_to_gates(read_dependencies_map, schedule_map):
    if schedule_map.is_empty():
        return None
    return schedule_map.reverse().apply_range(read_dependencies_map).as_map()


def filter_multi_qubit_gates(domain, read_dependencies, schedule):
    new_domain = extract_multi_qubit_gates(read_dependencies).coalesce()
    filtered_schedule = schedule.intersect_domain(new_domain)

    if filtered_schedule is None:
        return None, None, None

    new_read_dependicies = read_dependencies.intersect_domain(
        new_domain).coalesce()

    # new_schedule = rescheduling(filtered_schedule)
    new_schedule = filtered_schedule

    return new_domain, new_read_dependicies, new_schedule


def rescheduling(schedule):

    schedule_points_set = schedule.range()
    schedule_points_list = isl_set_to_python_list(schedule_points_set)

    schedule_points_list.sort()

    nb_points = len(schedule_points_list)

    compact_schedule_points_list = list(range(nb_points))

    dispersed_to_compact_schedule_map = isl.Map(
        "{" + ";".join(f"[{x}]->[{y}]" for x, y in zip(schedule_points_list, compact_schedule_points_list)) + "}")

    return schedule.apply_range(dispersed_to_compact_schedule_map)


def read_data(data):
    read = data['read']
    write = data["write"]

    # qops = read.as_map().domain().dim_max_val(0).to_python()

    # write_dict = isl_map_to_dict_optimized2(write_dep.as_map())
    # access_dict = isl_map_to_dict_optimized2(access.as_map())

    return read, write
