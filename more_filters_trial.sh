#!/bin/sh
#SBATCH --account=g.alex054
#SBATCH --job-name=more_filters
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=34:15:00
#SBATCH --output=log_more_filters.out
#SBATCH --mail-user=graduationprojectplease@gmail.com
#SBATCH --mail-type=ALL,TIME_LIMIT_10


python -u nutshell/occ_sep_adam_step_more_filters.py
