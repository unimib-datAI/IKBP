FROM rpozzi/blink:latest

# Upgrade PIP
RUN python3 -m pip install --upgrade pip

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --host 0.0.0.0 --port 80 --crossencoder_model $CROSSENCODER_MODEL --crossencoder_config $CROSSENCODER_CONFIG --postgres postgres://postgres:$POSTGRES_PASSWORD@postgres:5432/postgres
