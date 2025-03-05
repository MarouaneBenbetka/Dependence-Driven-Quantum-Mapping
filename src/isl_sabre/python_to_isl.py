
import islpy as isl


def dict_to_isl_map(input_dict: dict) -> str:
    """
    Convert a dictionary of {key: [values]} to an ISL Map string format.
    """

    entries = []
    for key, values in input_dict.items():
        for val in values:
            entries.append(f"[{key}]->[{val}]")
    if not entries:
        return isl.UnionMap("{}")

    return isl.Map("{" + ";".join(entries) + "}").coalesce()


def list_to_isl_set(input_list):
    if not input_list:
        return isl.UnionSet("{}")

    point_strings = []
    for item in input_list:
        point_strings.append(f"[{item}]")

    set_str = "{" + ";".join(point_strings) + "}"

    return isl.Set(set_str)

def int_to_isl_set(input):
    return isl.Set("{" + f"[{input}]" + "}")