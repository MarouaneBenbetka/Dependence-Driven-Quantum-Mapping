
import json
import islpy as isl
from src.isl_sabre.isl_to_python import isl_set_to_python_list


def json_file_to_isl(path: str):

    with open(path) as f:
        data = json.load(f)

    return {
        "domain": isl.UnionSet(data["Domain"]),
        "read_dependencies": isl.UnionMap(data["Read"]),
        "write_dependencies": isl.UnionMap(data["Write"]),
        "call": isl.UnionMap(data["Call"]),
        "schedule": isl.UnionMap(data["RecoveredSchedule"]),
        "Qops": data["Stats"]["Qops"],
        "qasm_code": data["qasm_code"]
    }


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

    #new_schedule = rescheduling(filtered_schedule)
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

    domain, read_dep, schedule = filter_multi_qubit_gates(
        data["domain"], data["read_dependencies"], data["schedule"])

    access = access_to_gates(read_dep, schedule)

    #qops = access.domain().count_val().to_python()
    qops =  access.domain().dim_max_val(0).to_python()
    write_dep = data["write_dependencies"]
    write_dep = schedule.reverse().apply_range(write_dep).as_map()
    
    read_dep = access_to_gates(data["read_dependencies"],data["schedule"])

    map_str = f"{{ [i] -> [{qops}-i - 1] : 0 <= i <= {qops} }}"
    reverse_map = isl.Map(map_str)
    reverse_access = access.apply_domain(reverse_map)
    reverse_schedule = schedule.apply_range(reverse_map)

    return qops, read_dep,access, reverse_access, schedule, reverse_schedule,write_dep
