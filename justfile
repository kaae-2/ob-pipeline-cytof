dry-run:
    ob run benchmark -b Clustering_conda.yml --local-storage --dry-run

run:
    ob run benchmark -b Clustering_conda.yml --local-storage --cores 4

add-dataset:
    python scripts/add_dataset.py --config Clustering_conda.yml

add-model:
    python scripts/add_model.py --config Clustering_conda.yml

validate-config:
    python scripts/validate_benchmark_config.py --config Clustering_conda.yml

check-config:
    just validate-config && just dry-run

pull:
    git pull

rerun:
    just pull && just run

recheck:
    just pull && just dry-run

push:
    git add . && git commit -m "update" && git push

ob-start:
    cd .. && conda activate omnibenchmark && cd cytof-benchmark
