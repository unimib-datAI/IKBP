FROM python:3.7

WORKDIR /home/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138 04EE7237B7D453EC && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip
    
# Install utils
RUN apt-get update && \
    apt-get -y install --no-install-recommends gcc

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --host 0.0.0.0 --port 80 $NILPREDICTOR_ARGS
