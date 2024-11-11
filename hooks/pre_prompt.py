import os, json, re, subprocess

cwd = os.getcwd()

# locate and pass the location of the replay file
replay_file_name = os.path.basename(cwd) + ".json"
replay_file_path = f"~/.cookiecutter_replay/{replay_file_name}"
replay_file = os.path.expanduser(replay_file_path)

# locate and pass the repository url
repository_url = None
result = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=False)
if result.returncode == 0:
    repository_url = result.stdout.strip()

# add values to cookiecutter configuraton before project generation
with open("cookiecutter.json", "r+") as file:
    data = json.load(file)
    data["_replay_file"] = replay_file
    data["_repository_url"] = repository_url
    file.seek(0)
    json.dump(data, file, indent=4)
