# Songbook

## Overview

The Songbook app is a simple app to host your own songbook database. It can be used to add your own chords in a chorpro format, edit them and print them in a single songbook.

## Installation

To get started with the Songbook app, make sure you have Docker and Docker Compose installed on your system.

### Docker Installation

Follow the instructions on the official Docker website to install Docker for your operating system:
[Install Docker](https://docs.docker.com/get-docker/)

### Docker Compose Installation

Docker Compose usually comes bundled with Docker Desktop on Windows and macOS. If you're using Linux or need to install Docker Compose separately, follow the instructions here:
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

### Backend data

Backend is running on following URL:

```bash
http://localhost:8000
```

You can access API documentation:

```bash
http://localhost:8000/docs
```

### Acknowledgments

https://www.chordpro.org/chordpro/support/
