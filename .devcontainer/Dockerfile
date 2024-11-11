FROM python:latest

ARG USERNAME='python'
ARG REQUIREMENTS='pyproject.toml'
ARG PROMPT='\e[0;36m\$\[\033[0m\] \e[0;32m\u\[\033[0m\] : \W λ '

ADD ${REQUIREMENTS} ${REQUIREMENTS}

RUN pip install --root-user-action=ignore --upgrade cookiecutter pip uv
RUN uv pip install --system --requirement=${REQUIREMENTS}

RUN groupadd --gid 1000 ${USERNAME} && \
    useradd --uid 1000 --gid 1000 -m ${USERNAME}

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN echo "PS1=\"${PROMPT}\"" >> ${HOME}/.bashrc
