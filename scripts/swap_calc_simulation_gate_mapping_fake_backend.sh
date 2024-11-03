#!/bin/bash

#Define the resource requirements here using #SBATCH

#SBATCH -p compute
##SBATCH --reservation=c2
#SBATCH --nodes=1
#SBATCH -c 1
#SBATCH --mem=64G
#SBATCH -t 2-1
#SBATCH -o /scratch/mb10324/Poly-Swap/scripts/swap_calc_simulation_gate_mapping_fake_backend.out
#SBATCH -e /scratch/mb10324/Poly-Swap/scripts/swap_calc_simulation_gate_mapping_fake_backend.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=mb10324@nyu.edu

#Resource requiremenmt commands end here

#Add the lines for running your code/application
module load miniconda-nobashrc
eval "$(conda shell.bash hook)"
module load gcc

#Activate any environments if required
conda activate main

#Execute the code

python /scratch/mb10324/Poly-Swap/single_benchmark.py