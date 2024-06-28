# Songbook

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

### Acknowledgments

<https://www.chordpro.org/chordpro/support/>
