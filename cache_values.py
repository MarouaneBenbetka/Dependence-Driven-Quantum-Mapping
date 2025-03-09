import os
import json
import argparse
from tqdm import tqdm

import islpy as isl

from src.isl_sabre.isl_to_python import isl_map_to_dict_optimized
from src.isl_sabre.poly_circuit_utils import json_file_to_isl, access_to_gates, filter_multi_qubit_gates


def main():
    parser = argparse.ArgumentParser(
        description="Process benchmark JSON files.")
    parser.add_argument(
        "--benchmark",
        required=True,
        help="Name of the benchmark folder to process (e.g., 'queko-bss-16qbt').",
    )
    args = parser.parse_args()
    benchmark = args.benchmark

    folder_path = os.path.join("benchmarks", "polyhedral", benchmark)
    output_folder = os.path.join(
        "benchmarks", "augmented", benchmark)

    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Directory does not exist: {folder_path}")
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")

    os.makedirs(output_folder, exist_ok=True)

    for file_name in tqdm(os.listdir(folder_path)):
        if not file_name.endswith(".json"):
            continue

        try:
            input_path = os.path.join(folder_path, file_name)
            with open(input_path) as f:
                file_dict = json.load(f)

            read_dependencies = isl.UnionMap(file_dict["Read"])
            schedule = isl.UnionMap(file_dict["RecoveredSchedule"])
            domain = isl.UnionSet(file_dict["Domain"])

            domain2, read_dependencies2, schedule2 = filter_multi_qubit_gates(
                domain, read_dependencies, schedule)

            access = access_to_gates(read_dependencies2, schedule2)
            access_dict = isl_map_to_dict_optimized(access)

            file_dict["access"] = access.to_str()
            file_dict["filtered_schedule"] = schedule2.to_str()

            output_json_path = os.path.join(output_folder, file_name)
            with open(output_json_path, "w") as json_file:
                json.dump(file_dict, json_file, indent=4)

            dict_file_name = file_name.replace(".json", "_access_dict.txt")
            dict_file_path = os.path.join(output_folder, dict_file_name)
            with open(dict_file_path, "w") as dict_file:
                dict_file.write(str(dict(access_dict)))
        except Exception as e:
            print(f"Error processing {file_name}: {e}", flush=True)
            continue


if __name__ == "__main__":
    main()
