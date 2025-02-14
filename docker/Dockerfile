FROM python:3.9

RUN pip install --no-cache-dir \
        fastapi \
        geopy \
        openai \
        opencv-python-headless \
        piexif \
        pillow \
        pymongo \
        python-multipart \
        requests \
        uvicorn

COPY --from=src ./app /app
COPY --from=src ./static /static
RUN mkdir -p /static_js_lib/ && curl https://unpkg.com/ol@7.3.0/dist/ol.js -o /static_js_lib/ol.js

WORKDIR /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
