import os, shutil

cwd = os.getcwd()

# copy the users replay file to the generated project
replay_file_source = "{{ cookiecutter._replay_file }}"
replay_file_destination = f"{cwd}/.cookiecutter.json"
shutil.copy(replay_file_source, replay_file_destination)
