FROM python:3.14-bookworm

# The official python:3.14-bookworm image (buildpack-deps based) already ships
# git, curl, and a C/C++ toolchain, which is everything Lakshya needs to build
# numpy/pandas wheels and let the agent operate. Add a non-root user to run as.
RUN useradd --create-home --shell /bin/bash ubuntu

USER ubuntu
WORKDIR /home/ubuntu

# Project-owned virtual environment so dependency installs never need root and
# `python`/`pip`/`pytest` resolve to the correct interpreter for both the
# install command and interactive/login shells the agent uses.
ENV VIRTUAL_ENV=/home/ubuntu/.venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN echo 'export PATH="/home/ubuntu/.venv/bin:$PATH"' >> /home/ubuntu/.bashrc \
    && echo 'export PATH="/home/ubuntu/.venv/bin:$PATH"' >> /home/ubuntu/.profile

RUN python -m pip install --upgrade pip
