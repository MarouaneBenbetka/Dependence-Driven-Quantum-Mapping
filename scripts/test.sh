#!/bin/bash

#Define the resource requirements here using #SBATCH

#SBATCH -p compute
##SBATCH --reservation=c2
#SBATCH --nodes=1
#SBATCH -c 64
#SBATCH --mem=128G
#SBATCH -t 5-0
#SBATCH -o /scratch/mb10325/Poly-Swap/scripts/test.out
#SBATCH -e /scratch/mb10325/Poly-Swap/scripts/test.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=mb10325@nyu.edu

#Resource requiremenmt commands end here

#Add the lines for running your code/application
module load miniconda-nobashrc
eval "$(conda shell.bash hook)"
module load gcc

#Activate any environments if required
conda activate main

#Execute the code

python /scratch/mb10325/Poly-Swap/main.py