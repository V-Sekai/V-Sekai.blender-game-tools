# Mixer Broadcaster Server

This is a server application written in Python. It can be launched from the command line and accepts several optional arguments to customize its behavior.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You need Python 3 installed on your system to run this application. You can download it from [here](https://www.python.org/downloads/).

### Installing

Clone the repository to your local machine:

```bash
git clone https://github.com/V-Sekai/mixer.git
```

Navigate to the directory where the repository is cloned:


## Usage

The script also accepts several command-line arguments:

- `--port`: This argument allows you to specify the port number on which the server should run. If not provided, it defaults to the value of `common.DEFAULT_PORT`.

- `--log-server-updates`: If this argument is included, the server will log updates.

- `--bandwidth`: This argument allows you to simulate bandwidth limitation. The value should be specified in megabytes per second.

- `--latency`: This argument allows you to simulate network latency. The value should be specified in milliseconds.

For example, to run the server on port 12800 with a simulated bandwidth limit of 10 Mbps and a latency of 100 ms, you would use the following command:

```bash
cd addons/mixer/addons
python -m mixer.broadcaster.apps.server --port 12800 --bandwidth 10 --latency 100
```