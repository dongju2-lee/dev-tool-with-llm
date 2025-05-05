FROM python:3.13-slim

WORKDIR /app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default environment variables (can be overridden at runtime)
ENV SONARQUBE_URL=http://sonarqube:9000
ENV SONARQUBE_TOKEN=""

# Expose port for HTTP/SSE MCP server
EXPOSE 8000

# Run the MCP server
CMD ["python", "sonarqube_mcp_server.py"] 