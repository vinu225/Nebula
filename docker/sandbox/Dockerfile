# Sovereign AI Workbench — Air-gapped Code Execution Sandbox
FROM python:3.12-slim

WORKDIR /workspace

# Install common scientific and data processing packages
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.2 \
    scipy==1.13.1 \
    matplotlib==3.8.4 \
    openpyxl==3.1.2 \
    sympy==1.12

# Create non-privileged unprivileged user
RUN useradd -m -u 1000 sandboxuser && \
    chown -R sandboxuser:sandboxuser /workspace

USER sandboxuser

ENTRYPOINT ["python"]
