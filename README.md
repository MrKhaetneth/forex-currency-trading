# Forex-Currency-Trading

This is a repository dedicated to the currency trading within Forex.

# System requirements and installation

I am assuming that you have a Linux OS (Kernel) or a Windows OS but with WSL2. I am using Windows OS with WSL2 via Ubuntu 24.04. If you do not have Ubuntu 24.04 yet, I recommend you install it first. For those with Linux OS, you can skip this part. As for Windows OS user, open up your powershell and run the following command

```powershell
wsl --install -d Ubuntu-24.04
```

After that, open up your Ubuntu 24.04 and run this bash script

```bash
$ sudo apt update && sudo apt install -y build-essential git curl wget
```

# Python with UV

Instead of the usual `pip` Python package manager, we will be using `uv` instead because `uv` handles package and downloads them a LOT faster (on average 5-10 times.) And we will be working with what is known as *virtual environment*. `uv` comes with a built-in feature of managing and working within this virtual environment in the background so it doesn't require us to run lots of commands.

Navigate to the project's folder and let us first install `uv`.

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

After this, all you need to run is a single line to sync your entire working environment with that of the repository!

```bash
$ uv sync
```

