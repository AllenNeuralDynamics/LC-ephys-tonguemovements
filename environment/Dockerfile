# hash:sha256:2e986011032f62d32c9f0c8a6bdec40fd30fdc1642dfd1e39cfe52a608f98f19
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/jupyterlab:3.6.1-miniconda4.12.0-python3.9-ubuntu20.04
 
ARG DEBIAN_FRONTEND=noninteractive
ARG AWS_ACCESS_KEY_ID
ARG AWS_DEFAULT_REGION
ARG AWS_SECRET_ACCESS_KEY
 
ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-ask-pass /
 
RUN python -m pip install --upgrade pip

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1-mesa-glx=21.2.6-0ubuntu0.1~20.04.2 \
        pkg-config=0.29.1-0ubuntu4 \
        build-essential=12.8ubuntu1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U --no-cache-dir \
    boto3==1.41.5 \
    aind-ephys-utils==0.0.15 \
    hdmf-zarr==0.11.0 \
    ipywidgets==7.7.2 \
    open-ephys-python-tools==0.1.7 \
    pillow==10.3.0 \
    pyarrow==21.0.0 \
    pymupdf==1.24.2 \
    pynwb==3.0.0 \
    pypdf2==3.0.1 \
    scipy==1.13.0 \
    seaborn==0.13.2 \
    spikeinterface[full]==0.100.0 \
    statsmodels==0.14.2 \
    wavpack-numcodecs==0.1.5 \
    zarr==2.18.2 \
    aind-dynamic-foraging-data-utils==0.1.48 \
    aind_dynamic_foraging_basic_analysis==0.4.2 \
    git+https://github.com/AllenNeuralDynamics/aind-dynamic-foraging-behavior-video-analysis@44de8f82bef424221a909736d6ae9a1c8e8363a3 \
    opencv_python==4.11.0.86 \
    moviepy==1.0.3 \
    scikit-image==0.24.0 \
    trimesh==4.11.0


COPY postInstall /
RUN /postInstall