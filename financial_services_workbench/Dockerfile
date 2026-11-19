FROM python:3.12-slim

WORKDIR /opt/fsw
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FS_LLM_PROVIDER=mock \
    NVIDIA_API_BASE_URL=https://integrate.api.nvidia.com/v1 \
    NVIDIA_MODEL=meta/llama-3.3-70b-instruct \
    FSW_MCP_HOST=0.0.0.0 \
    FSW_MCP_PORT=8765 \
    PYTHONUNBUFFERED=1

EXPOSE 8765
CMD ["python", "-m", "fsw.mcp_server"]
