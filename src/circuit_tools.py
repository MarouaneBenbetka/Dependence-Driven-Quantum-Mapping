
import re



def extract_multi_qubit_gates(access_map):
    return access_map.subtract(  access_map.lexmin().intersect(access_map.lexmax())).domain()


def access_to_gates( read_dependencies_map , schedule_map):
    return schedule_map.reverse().apply_range(read_dependencies_map).as_map()


def filter_multi_qubit_gates(domain,access,schedule):
    new_domain = extract_multi_qubit_gates(access).coalesce()
    new_schedule = access_to_gates(access,schedule.intersect_domain(new_domain)).coalesce()
    new_read_dependicies = access.intersect_domain(new_domain).coalesce()

    return new_domain,new_read_dependicies,new_schedule

def get_qubits_needed(read_dependencies):
    return read_dependencies.range().as_set().lexmax().dim_max_val(0).to_python()+1