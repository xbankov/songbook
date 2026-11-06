# Songbook

![CI](https://github.com/xbankov/songbook/actions/workflows/system.yaml/badge.svg)
[![codecov](https://codecov.io/github/xbankov/songbook/graph/badge.svg?token=j2WY740c87)](https://codecov.io/github/xbankov/songbook)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/50033becb22e4ad3b819448f2a567712)](https://app.codacy.com/gh/xbankov/songbook/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

## Overview

The Songbook app is a simple app to host your own songbook database. It can be used to add your own chords in a chorpro format, edit them and print them in a songbook.

## Installation

To get started with the Songbook app, make sure you have Docker and Docker Compose installed on your system.

### Docker Installation

Follow the instructions on the official Docker website to install Docker for your operating system:
[Install Docker](https://docs.docker.com/get-docker/)

### Docker Compose Installation

Docker Compose usually comes bundled with Docker installation. If you need to install Docker Compose separately, follow the instructions here:
[Install Docker Compose](https://docs.docker.com/compose/install/)

## Building and Running the App

Once you have Docker and Docker Compose installed, building and running the Songbook app is straightforward.

### Build

To build the Docker images for the Songbook app, navigate to the project directory in your terminal and run the following command:

```bash
docker compose build
```

This command will download the necessary dependencies and build the Docker images for the app.

### Run

After the build process is complete, you can start the Songbook app by running the following command:

```bash
docker compose up
```

### Accessing the App

Once the app is up and running, you can access it by opening your web browser and navigating to the following URL:

```bash
http://localhost:8080
```

You can access API documentation:

```bash
http://localhost:8000/docs
```

## Cloud Deployment

Using MongoDB Atlas (database) and Google Cloud Run (backend)

Create an account and database and copy `database uri`.
<https://www.mongodb.com/products/platform/atlas-database>

Set `MONGODB_URI="<your-database-uri"` before running the application with local backend or put as environmental variable in cloud settings.

Follow this guide to build and deploy backend as docker container to google cloud.
**Hint:** setup maximum instances to 2-3 to save yourself money against DDoS attacks, infinite loop code or sudden spike of interests in your platform.

<https://github.com/sekR4/FastAPI-on-Google-Cloud-Run>

Optional: Use domain name for the app.

## Dev Mode

To access devmode (changes immediatelly applied), it is recommended to run `docker compose up` to spin up `mongodb` and run *dev* version of backend using this .vscode configurations:

```yaml
"cwd": "${workspaceFolder}/backend/src",
"module": "uvicorn",
"args": ["main:app", "--reload", "--port", "8001"],
"jinja": true,
"env": {
    "MONGODB_HOST": "localhost",
},
```

Which could roughly translate to run this in terminal inside `/songbook/backend/src`:

```bash
env MONGODB_HOST=localhost python3 -m uvicorn main:app --reload --port 8001
```

### Standards

Install pre-commit hook

```bash
pip install pre-commit
pre-commit install
```

## AI maintainer

An AI maintainer bot (`xbankov-ai-maintainer[bot]`) helps with issues in this
repository. It only works on issues a maintainer allows, and it **never merges**:
a human always reviews and merges.

### Labels

| Label | Set by | Meaning |
| --- | --- | --- |
| `ai-allowed` | Maintainer | The bot may work on this issue. Ignored if someone else adds it. Remove it to stop the work. |
| `ai:queued` | Bot | Allowed, waiting its turn. The bot works on one issue at a time. |
| `ai:running` | Bot | The bot is analysing the issue or writing the code. |
| `ai:waiting-for-review` | Bot | A maintainer needs to act: approve a proposal or review a pull request. |

The `ai:` labels only show the status. Changing them by hand has no effect.

### Commands

Maintainers write these as the first line of an issue comment:

- `/ai approve` — implement the current proposal.
- `/ai reject` — do not implement it.
- `/ai revise <what to change>` — get a new proposal with your guidance.

### How it works

1. A maintainer adds `ai-allowed` to an issue.
2. The bot posts a proposal as a comment.
3. A maintainer replies `/ai approve`, `/ai reject` or `/ai revise …`.
4. After approval, the bot opens a pull request and waits for CI.
5. A maintainer reviews and merges the pull request.

### Acknowledgments

<https://www.chordpro.org/chordpro/support/>
