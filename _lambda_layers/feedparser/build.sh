LAYER_NAME="$1"

docker run --platform=linux/amd64 -v "$PWD":/var/task build-container \
    /bin/bash -c "pip3 install -r requirements.txt -t python/lib/python3.9/site-packages/; exit"

zip -r ${LAYER_NAME}.zip python > /dev/null

aws lambda publish-layer-version --layer-name ${LAYER_NAME} --description "Layer containing ${LAYER_NAME} module" --zip-file fileb://${LAYER_NAME}.zip --compatible-runtimes "python3.9"
