
import json
import islpy as isl


def json_file_to_isl(path:str):

    with open(path) as f:
        data = json.load(f)
    
    return {
        "domain": isl.UnionSet(data["Domain"]),
        "read_dependencies": isl.UnionMap(data["Read"]),
        "write_dependencies": isl.UnionMap(data["Write"]),
        "call": isl.UnionMap(data["Call"]),
        "schedule":isl.UnionMap(data["RecoveredSchedule"]),
        "Qops":data["Stats"]["Qops"],
        "qasm_code":data["qasm_code"]
    }

def extract_multi_qubit_gates(access_map):
    return access_map.subtract(  access_map.lexmin().intersect(access_map.lexmax())).domain()

def access_to_gates( read_dependencies_map , schedule_map):
    if schedule_map.is_empty():
        return None
    return schedule_map.reverse().apply_range(read_dependencies_map).as_map()

def filter_multi_qubit_gates(domain ,access ,schedule):
    new_domain = extract_multi_qubit_gates(access).coalesce()
    new_schedule = access_to_gates(access,schedule.intersect_domain(new_domain))
    if new_schedule is None:
        return None,None,None
    new_read_dependicies = access.intersect_domain(new_domain).coalesce()

    return new_domain,new_read_dependicies,new_schedule

def read_data(data):
    qops = data["Qops"]
    _, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
    origin_schedule = data["schedule"]
    schedule = origin_schedule.intersect_domain(read_dep.domain())


    map_str = f"{{ [i] -> [{qops}-i - 1] : 0 <= i < {qops} }}"
    reverse_map = isl.Map(map_str)
    reverse_access = access.apply_domain(reverse_map)
    reverse_schedule = schedule.apply_range(reverse_map)
    
    return qops, read_dep, access, reverse_access, schedule, reverse_schedule