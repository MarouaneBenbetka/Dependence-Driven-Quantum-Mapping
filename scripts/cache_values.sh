#!/bin/bash
#SBATCH -p compute
#SBATCH --nodes=1
#SBATCH -c 16
#SBATCH --mem=64G
##SBATCH --reservation=c2
#SBATCH -t 5-0
#SBATCH -o /scratch/mb10324/Poly-Swap/out/%x_%j.out
#SBATCH -e /scratch/mb10324/Poly-Swap/err/%x_%j.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=mb10324@nyu.edu

# Check if a benchmark name was provided as an argument
if [ $# -lt 1 ]; then
    echo "Usage: $0 <benchmark>"
    exit 1
fi

# Capture the benchmark name
BENCHMARK=$1
echo "Running benchmark: ${BENCHMARK}"

# Load modules and activate conda environment
module load miniconda-nobashrc
eval "$(conda shell.bash hook)"
module load gcc
conda activate main

# Execute the Python script with the benchmark parameter
python /scratch/mb10325/Poly-Swap/cache-values.py --benchmark "${BENCHMARK}"
