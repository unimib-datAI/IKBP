FROM openjdk:8u282-jre

ARG URL=https://dhsite.fbk.eu/tint-release/0.3/tint-0.3-complete.tar.gz

WORKDIR /app

RUN wget $URL -O /app/tint.tar.gz

RUN tar -xzf /app/tint.tar.gz && \
    rm /app/tint.tar.gz

WORKDIR /app/tint

ENTRYPOINT ["./tint-server.sh"]

EXPOSE 8012

CMD ["-p", "8012"]