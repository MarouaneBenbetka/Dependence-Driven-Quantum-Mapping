
import json
import islpy as isl
from src.isl_routing.utils.isl_to_python import isl_set_to_python_list, isl_map_to_dict_optimized2
import os
import ast


def json_file_to_isl(file_path: str):

    with open(file_path) as f:
        data = json.load(f)

    domain = isl.UnionSet(data["Domain"])

    read_dependencies = isl.UnionMap(data["Read"])

    write_dependencies = isl.UnionMap(data["Write"])

    call = isl.UnionMap(data["Call"])

    schedule = isl.UnionMap(data["RecoveredSchedule"])
    qops = data["Stats"]["Qops"]
    qasm_code = data["qasm_code"]

    access = None
    filtered_schedule = None

    result = {
        "domain": domain,
        "read_dependencies": read_dependencies,
        "write_dependencies": write_dependencies,
        "call": call,
        "schedule": schedule,
        "Qops": qops,
        "qasm_code": qasm_code,
        "access":   access,
        "filtered_schedule": filtered_schedule
    }

    access_dict_path = file_path.replace(".json", "_access_dict.txt")
    if os.path.exists(access_dict_path):
        with open(access_dict_path, "r") as f:
            content = f.read()
            # Convert the string content into a Python dictionary
            try:
                data_dict = ast.literal_eval(content)
                result["access_dict"] = data_dict
            except Exception as e:
                result["access_dict"] = None
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


def read_data(data, with_write_dep=True, with_reverse=False):
    access = None
    schedule = None

    if "filtered_schedule" in data and data["filtered_schedule"] is not None and "access" in data and data["access"] is not None:
        schedule = data["filtered_schedule"]
        access = data["access"]
    else:
        #domain, read_dep, schedule = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
        domain, read_dep, schedule = data['domain'], data['read_dependencies'], data['schedule']
        access = access_to_gates(read_dep, schedule)
    # qops = access.domain().count_val().to_python()

    qops = access.domain().dim_max_val(0).to_python()

    if with_write_dep:
        write_dep = data["write_dependencies"]
        write_dep = schedule.reverse().apply_range(write_dep).as_map()
        write_dict = isl_map_to_dict_optimized2(write_dep)
    else:
        write_dep = None

    if "access" in data and data["access"]:
        access_dict = data["access"]
    else:
        access_dict = isl_map_to_dict_optimized2(access)

    return qops, access, access_dict, schedule, write_dep,write_dict
