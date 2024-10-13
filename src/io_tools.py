
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
        "Qops":data["Stats"]["Qops"]
    }