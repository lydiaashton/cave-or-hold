# The tested model's sandbox. Python patch version and every package, including
# the ones the main libraries pull in, are pinned, so an image built on another
# machine or another day runs the model's code against identical versions.
FROM python:3.11.18-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt
# The container gets 1 CPU, but numpy's BLAS sees every host core and starts a
# thread per core. Measured 13 Nov on a 22-core host: a two-way fixed effects
# regression on a confounded-world file took 288 s with the default threads and
# 1.3 s with one, so the default would make the standard analysis time out in
# that world only, and by an amount that depends on the machine's core count.
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
