FROM python:3.13-slim

WORKDIR /app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default environment variables (can be overridden at runtime)
ENV GRAFANA_URL=http://grafana:3000
ENV GRAFANA_API_KEY=""

# Expose port for HTTP/SSE MCP server
EXPOSE 8000

# Run the MCP server with SSE transport
# Reference: https://modelcontextprotocol.io/llms-full.txt
CMD ["python", "grafana_mcp_server.py"]