docker build -t rtklib_demo5_img .

docker rm -f RTKLIB-linux || true


xhost +local:docker
docker run -it --name RTKLIB-linux -e DISPLAY=$DISPLAY -v ~/Downloads/app:/app \
    -v "$(pwd)":/code2 \
     --network optuna-net \
    -v /tmp/.X11-unix:/tmp/.X11-unix rtklib_demo5_img \
    bash

docker exec RTKLIB-linux sh -c "echo hi"