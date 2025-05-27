# Docker Instructions for Slack MCP Server (SSE)

This document provides instructions for building, running, and publishing the Slack MCP Server with SSE transport using Docker.

## Local Development

### Prerequisites

- Docker and Docker Compose installed
- Slack Bot Token and Team ID

### Obtaining Slack Bot Token and Team ID

1. Create a Slack App:
   - Visit the [Slack Apps page](https://api.slack.com/apps)
   - Click "Create New App"
   - Choose "From scratch"
   - Name your app and select your workspace

2. Configure Bot Token Scopes:
   - Navigate to "OAuth & Permissions" in your app settings
   - Add these scopes:
     - `channels:history` - View messages and other content in public channels
     - `channels:read` - View basic channel information
     - `chat:write` - Send messages as the app
     - `reactions:write` - Add emoji reactions to messages
     - `users:read` - View users and their basic information

3. Install App to Workspace:
   - Click "Install to Workspace" and authorize the app
   - Save the "Bot User OAuth Token" that starts with `xoxb-`

4. Get your Team ID:
   - Open Slack in a web browser
   - Once logged in, check the URL in your browser
   - The URL will be in a format like: `https://app.slack.com/client/T01234567/...`
   - Your Team ID is the string beginning with T (e.g., `T01234567`)

### Building and Running Locally

1. Create a `.env` file with your Slack credentials:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_TEAM_ID=your-slack-team-id
PORT=3000
```

2. Build and run the container using Docker Compose:

```bash
docker compose up --build
```

3. The server will be available at `http://localhost:3000` with the SSE endpoint at `http://localhost:3000/sse`.

## Publishing to GitHub Container Registry (ghcr.io)

### Prerequisites

- GitHub account with access to the repository
- Personal Access Token (PAT) with `write:packages` scope
- Docker installed

### Steps to Publish

1. Log in to GitHub Container Registry:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

Replace `$GITHUB_TOKEN` with your GitHub Personal Access Token and `USERNAME` with your GitHub username.

2. Build the Docker image with the appropriate tag:

```bash
docker build -t ghcr.io/dvelopment/slack-mcp-server-sse:latest .
```

3. Push the image to GitHub Container Registry:

```bash
docker push ghcr.io/dvelopment/slack-mcp-server-sse:latest
```

4. To tag and push a specific version:

```bash
docker build -t ghcr.io/dvelopment/slack-mcp-server-sse:1.0.0 .
docker push ghcr.io/dvelopment/slack-mcp-server-sse:1.0.0
```

## Using the Published Image

To use the published image in your Docker Compose file:

```yaml
version: '3.8'

services:
  slack-mcp-server:
    image: ghcr.io/dvelopment/slack-mcp-server-sse:latest
    ports:
      - "${PORT:-3000}:${PORT:-3000}"
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_TEAM_ID=${SLACK_TEAM_ID}
      - PORT=${PORT:-3000}
    restart: unless-stopped
```

## GitHub Actions Workflow

You can automate the build and publish process using GitHub Actions. Here's a sample workflow file:

```yaml
name: Build and Publish Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ghcr.io/dvelopment/slack-mcp-server-sse
          tags: |
            type=semver,pattern={{version}}
            type=ref,event=branch
            type=sha,format=short

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Save this file as `.github/workflows/docker-publish.yml` in your repository to enable automatic builds.